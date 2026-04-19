"""Tests for REQ-11: Session name sanitization."""
from __future__ import annotations

import pytest

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestSessionNameSanitization:
    """REQ-11: _sanitize_session_name SHALL strip tmux-invalid characters."""

    def test_valid_name_unchanged(self) -> None:
        """Names with only valid chars pass through unchanged."""
        assert TmuxOrchestrator._sanitize_session_name("fork-agent-abc123") == "fork-agent-abc123"

    def test_colons_replaced(self) -> None:
        """Colons SHALL be replaced with dashes."""
        assert TmuxOrchestrator._sanitize_session_name("agent:type") == "agent-type"

    def test_dots_replaced(self) -> None:
        """Dots SHALL be replaced with dashes."""
        assert TmuxOrchestrator._sanitize_session_name("agent.v2") == "agent-v2"

    def test_brackets_replaced(self) -> None:
        """Square brackets SHALL be replaced with dashes."""
        assert TmuxOrchestrator._sanitize_session_name("agent[0]") == "agent-0"

    def test_all_invalid_chars_in_one(self) -> None:
        """All four invalid chars in one name are all replaced."""
        assert TmuxOrchestrator._sanitize_session_name("a.b:c[d]e") == "a-b-c-d-e"

    def test_empty_after_sanitize_raises(self) -> None:
        """If name becomes empty after sanitization, raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            TmuxOrchestrator._sanitize_session_name("...:::")

    def test_leading_trailing_dashes_stripped(self) -> None:
        """REQ-11.5: Leading/trailing dashes SHALL be stripped after replacement."""
        assert TmuxOrchestrator._sanitize_session_name(".hidden") == "hidden"

    def test_trailing_dashes_stripped(self) -> None:
        """REQ-11.5: Trailing dashes from bracket replacement are stripped."""
        assert TmuxOrchestrator._sanitize_session_name("agent[0]") == "agent-0"

    def test_whitespace_name_raises(self) -> None:
        """Pure whitespace name raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            TmuxOrchestrator._sanitize_session_name("   ")
