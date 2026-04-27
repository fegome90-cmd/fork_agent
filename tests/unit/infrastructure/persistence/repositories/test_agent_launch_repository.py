"""Unit tests for SqliteAgentLaunchRepository.

Focuses on edge cases in claim() IntegrityError handling (H2):
  - duplicate key (partial unique index) → returns None
  - duplicate launch_id (PRIMARY KEY) → returns None (same catch block)
  - NOT NULL violation → raises RepositoryError (not silently suppressed)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.agent_launch_repository import (
    SqliteAgentLaunchRepository,
)


@pytest.fixture
def db(tmp_path: Path) -> DatabaseConnection:
    """SQLite with migrations applied."""
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    migrations_dir = project_root / "src" / "infrastructure" / "persistence" / "migrations"
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config=config)


@pytest.fixture
def repo(db: DatabaseConnection) -> SqliteAgentLaunchRepository:
    return SqliteAgentLaunchRepository(connection=db)


def _claim_kwargs(overrides: dict | None = None) -> dict:
    """Default claim() kwargs."""
    kw = {
        "launch_id": "launch-1",
        "canonical_key": "task:t-1",
        "surface": "polling",
        "owner_type": "task",
        "owner_id": "t-1",
        "lease_expires_at": 9999999999999,
    }
    kw.update(overrides or {})
    return kw


class TestClaimDuplicateKeyReturnsNone:
    """Duplicate canonical_key (partial unique index) → returns None."""

    def test_duplicate_canonical_key_returns_none(self, repo: SqliteAgentLaunchRepository) -> None:
        first = repo.claim(**_claim_kwargs())
        assert first is not None

        second = repo.claim(**_claim_kwargs({"launch_id": "launch-2"}))
        assert second is None

    def test_duplicate_launch_id_also_returns_none(self, repo: SqliteAgentLaunchRepository) -> None:
        """PRIMARY KEY violation on launch_id → message contains 'unique' → returns None."""
        repo.claim(**_claim_kwargs())
        # Same launch_id, different canonical_key → PRIMARY KEY violation
        result = repo.claim(**_claim_kwargs({"canonical_key": "task:t-different"}))
        assert result is None

    def test_different_canonical_keys_both_succeed(self, repo: SqliteAgentLaunchRepository) -> None:
        first = repo.claim(**_claim_kwargs())
        assert first is not None

        second = repo.claim(**_claim_kwargs({"launch_id": "launch-2", "canonical_key": "task:t-2"}))
        assert second is not None


class TestIntegrityErrorMessageClassification:
    """Verify that NOT NULL violations produce messages WITHOUT 'unique'.

    The claim() catch block distinguishes errors by checking for 'unique' in
    the message. NOT NULL violations don't contain 'unique', so they would
    correctly raise RepositoryError instead of returning None.
    """

    def test_not_null_error_message_lacks_unique(self, repo: SqliteAgentLaunchRepository) -> None:
        """NOT NULL IntegrityError message must NOT contain 'unique' keyword."""
        import sqlite3

        with repo._connection as conn:
            with pytest.raises(sqlite3.IntegrityError) as exc_info:
                conn.execute(
                    """INSERT INTO agent_launch_registry
                       (launch_id, canonical_key, surface, status, created_at,
                        reserved_at, lease_expires_at, owner_id)
                       VALUES (?, ?, ?, 'RESERVED', ?, ?, ?, ?)""",
                    ("bad-launch", "key", "polling", 100, 100, 999, "t-1"),
                )
            msg = str(exc_info.value).lower()
            assert "unique" not in msg, (
                f"NOT NULL violation message should not contain 'unique': {exc_info.value}"
            )
            assert "not null" in msg


class TestClaimHappyPath:
    """Verify claim returns a valid AgentLaunch on first insert."""

    def test_first_claim_succeeds(self, repo: SqliteAgentLaunchRepository) -> None:
        launch = repo.claim(**_claim_kwargs())
        assert launch is not None
        assert launch.launch_id == "launch-1"
        assert launch.canonical_key == "task:t-1"
        assert launch.status.value == "RESERVED"
