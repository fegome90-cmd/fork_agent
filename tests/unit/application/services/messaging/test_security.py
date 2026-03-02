"""Security tests: loop guard and broadcast allowlist."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.messaging.agent_messenger import (
    ALLOWED_SESSION_PREFIXES,
    AgentMessenger,
    _is_allowed_target,
)
from src.application.services.messaging.message_protocol import is_self_message
from src.domain.entities.message import AgentMessage, MessageType


class TestIsSelfMessage:
    """Unit tests for is_self_message() loop guard."""

    def test_returns_true_when_from_agent_matches(self) -> None:
        msg = AgentMessage.create(
            from_agent="fork-agent:0",
            to_agent="fork-other:0",
            message_type=MessageType.COMMAND,
            payload="hello",
        )
        assert is_self_message(msg, "fork-agent:0") is True

    def test_returns_false_when_from_agent_differs(self) -> None:
        msg = AgentMessage.create(
            from_agent="fork-sender:0",
            to_agent="fork-receiver:0",
            message_type=MessageType.COMMAND,
            payload="hello",
        )
        assert is_self_message(msg, "fork-receiver:0") is False

    def test_returns_false_for_different_window(self) -> None:
        msg = AgentMessage.create(
            from_agent="fork-agent:0",
            to_agent="fork-agent:1",
            message_type=MessageType.REPLY,
            payload="pong",
        )
        assert is_self_message(msg, "fork-agent:1") is False


class TestIsAllowedTarget:
    """Unit tests for _is_allowed_target() allowlist."""

    @pytest.mark.parametrize("name", ["fork-abc123", "fork-opencode-xyz", "agent-worker"])
    def test_allowed_prefixes_pass(self, name: str) -> None:
        assert _is_allowed_target(name) is True

    @pytest.mark.parametrize("name", ["personal", "29", "nvim", "test_e2e_bc_unique_1", ""])
    def test_non_allowed_names_fail(self, name: str) -> None:
        assert _is_allowed_target(name) is False

    def test_allowed_prefixes_constant_contains_expected(self) -> None:
        assert "fork-" in ALLOWED_SESSION_PREFIXES
        assert "agent-" in ALLOWED_SESSION_PREFIXES


class TestBroadcastAllowlist:
    """Integration tests: broadcast() skips non-allowlisted sessions."""

    def _make_messenger(self, tmp_path: Path) -> tuple[AgentMessenger, MagicMock]:
        from src.infrastructure.persistence.message_store import MessageStore
        from src.infrastructure.tmux_orchestrator import TmuxOrchestrator, TmuxSession, TmuxWindow

        store = MessageStore(db_path=tmp_path / "test.db")
        orchestrator = MagicMock(spec=TmuxOrchestrator)

        def make_session(name: str, window_index: int = 0) -> TmuxSession:
            return TmuxSession(
                name=name,
                windows=(TmuxWindow(session_name=name, window_index=window_index, window_name="main", active=True),),
                attached=False,
            )

        return AgentMessenger(orchestrator=orchestrator, store=store), orchestrator

    def test_broadcast_skips_non_allowlisted_session(self, tmp_path: Path) -> None:
        from src.infrastructure.tmux_orchestrator import TmuxSession, TmuxWindow

        messenger, orchestrator = self._make_messenger(tmp_path)

        orchestrator.get_sessions.return_value = [
            TmuxSession(
                name="personal-terminal",
                windows=(TmuxWindow("personal-terminal", 0, "bash", True),),
                attached=True,
            ),
        ]

        count = messenger.broadcast(from_agent="fork-agent:0", payload="test")
        assert count == 0
        orchestrator.send_message.assert_not_called()

    def test_broadcast_sends_only_to_allowlisted(self, tmp_path: Path) -> None:
        from src.infrastructure.tmux_orchestrator import TmuxSession, TmuxWindow

        messenger, orchestrator = self._make_messenger(tmp_path)
        orchestrator.send_message.return_value = True

        orchestrator.get_sessions.return_value = [
            TmuxSession(
                name="fork-agent-abc",
                windows=(TmuxWindow("fork-agent-abc", 0, "main", True),),
                attached=False,
            ),
            TmuxSession(
                name="personal",
                windows=(TmuxWindow("personal", 0, "zsh", True),),
                attached=True,
            ),
        ]

        count = messenger.broadcast(from_agent="fork-leader:0", payload="go")
        assert count == 1  # Only fork-agent-abc
        orchestrator.send_message.assert_called_once()

    def test_broadcast_logs_warning_for_skipped_session(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from src.infrastructure.tmux_orchestrator import TmuxSession, TmuxWindow

        messenger, orchestrator = self._make_messenger(tmp_path)

        orchestrator.get_sessions.return_value = [
            TmuxSession(
                name="nvim",
                windows=(TmuxWindow("nvim", 0, "editor", True),),
                attached=True,
            ),
        ]

        with caplog.at_level(logging.WARNING, logger="src.application.services.messaging.agent_messenger"):
            messenger.broadcast(from_agent="fork-agent:0", payload="test")

        assert any("not_allowlisted" in r.getMessage() or "not in allowlist" in r.getMessage() for r in caplog.records)
