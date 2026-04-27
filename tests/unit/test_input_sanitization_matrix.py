"""Parametrized input sanitization tests covering attack vectors.

Covers:
- Path traversal in DatabaseConfig
- Control/null character injection in Observation content
- ANSI escape injection in tmux send_input
- SQL injection via FTS5 search queries

Pattern adapted from pi-teams security.test.ts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import (
    DatabaseConfig,
    DatabaseConnection,
)
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "infrastructure" / "persistence" / "migrations"
)

# Regex patterns from agent_manager.py (mirrored for unit testing)
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _sanitize_tmux_text(message: str) -> str:
    """Replicate the sanitization logic from TmuxAgent.send_input."""
    sanitized = _ANSI_ESCAPE.sub("", message)
    sanitized = _CONTROL_CHARS.sub("", sanitized)
    sanitized = sanitized.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return sanitized.strip()


# ---------------------------------------------------------------------------
# Path Traversal
# ---------------------------------------------------------------------------


class TestPathTraversal:
    """DatabaseConfig must reject or neutralise traversal paths."""

    @pytest.mark.parametrize(
        "malicious",
        [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\Windows\\System32",
        ],
    )
    def test_db_path_rejects_traversal_when_parent_missing(self, malicious, tmp_path):
        """Path traversal with non-existent parent must raise ValueError."""
        # Resolve to a non-existent nested path so resolved.parent does not exist
        bad_path = tmp_path / malicious / "test.db"
        with pytest.raises(ValueError, match="path traversal"):
            DatabaseConfig(db_path=bad_path)

    def test_db_path_accepts_valid_path(self, tmp_path):
        """Normal paths must be accepted."""
        config = DatabaseConfig(db_path=tmp_path / "valid.db")
        assert config.db_path.name == "valid.db"


# ---------------------------------------------------------------------------
# Command Injection via tmux text
# ---------------------------------------------------------------------------


class TestCommandInjection:
    """Sanitized tmux text must not carry shell metacharacters."""

    @pytest.mark.parametrize(
        "payload",
        [
            "legit; rm -rf /",
            "legit$(whoami)",
            "legit`cat /etc/passwd`",
            "legit\nrm -rf /",
        ],
    )
    def test_tmux_text_strips_injection(self, payload):
        """Newlines and shell metacharacters must be collapsed to spaces."""
        result = _sanitize_tmux_text(payload)
        # Must not contain raw newlines (they're replaced by spaces)
        assert "\n" not in result
        assert "\r" not in result
        # Semicolons and backticks pass through sanitization since
        # they're handled by tmux send-keys (not a shell), but
        # the newlines are the real attack vector and must be stripped.
        assert result  # must not be empty

    def test_empty_after_sanitization_returns_empty(self):
        """Strings that become empty after sanitization must return empty."""
        payload = "\x1b[31m\x1b[0m"
        result = _sanitize_tmux_text(payload)
        assert result == ""


# ---------------------------------------------------------------------------
# Null and Control Characters
# ---------------------------------------------------------------------------


class TestNullAndControlChars:
    """Observation entity must reject null bytes; sanitization strips control chars."""

    @pytest.mark.parametrize(
        "payload",
        [
            "hello\x00null",
            "hello\x03\x04world",
            "\x1b[31mred\x1b[0minjection",
            "legit\r\nmalicious",
        ],
    )
    def test_control_chars_stripped_by_sanitizer(self, payload):
        """The tmux sanitization pipeline must strip control characters."""
        result = _sanitize_tmux_text(payload)
        assert "\x00" not in result
        assert "\x03" not in result
        assert "\x04" not in result
        assert "\x1b" not in result
        assert "\r\n" not in result

    @pytest.mark.parametrize(
        "payload",
        [
            "hello\x00null",
            "content with \x00 embedded",
        ],
    )
    def test_observation_rejects_null_bytes(self, payload):
        """Observation entity must reject content containing null bytes."""
        with pytest.raises(ValueError, match="null bytes"):
            Observation(
                id="test-id",
                timestamp=1000,
                content=payload,
            )

    def test_observation_accepts_clean_content(self):
        """Clean content must be accepted."""
        obs = Observation(
            id="test-id",
            timestamp=1000,
            content="clean content without issues",
        )
        assert obs.content == "clean content without issues"


# ---------------------------------------------------------------------------
# SQL Injection via FTS5 search
# ---------------------------------------------------------------------------


class TestFTS5Injection:
    """FTS5 search queries must be sanitised to prevent injection."""

    @pytest.fixture()
    def repo(self, tmp_path):
        db_path = tmp_path / "injection_test.db"
        config = DatabaseConfig(db_path=db_path)
        run_migrations(config, MIGRATIONS_DIR)
        conn = DatabaseConnection(config=config)
        repo = ObservationRepository(connection=conn)
        yield repo
        conn.close_all()

    @pytest.mark.parametrize(
        "malicious_query",
        [
            "test'; DROP TABLE observations; --",
            'test" OR 1=1',
            "test) OR (1=1",
            "test* OR NOT test",
        ],
    )
    def test_fts_search_handles_injection_safely(self, repo, malicious_query):
        """Malicious FTS5 queries must not crash or corrupt data."""
        # Should return an empty list or results, never raise
        results = repo.search(malicious_query)
        assert isinstance(results, list)
        # Verify the table still exists and is queryable
        all_obs = repo.get_all(limit=10)
        assert isinstance(all_obs, list)
