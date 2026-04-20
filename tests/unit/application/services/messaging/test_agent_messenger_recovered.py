"""Tests for AgentMessenger service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.database import DatabaseConnection
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.tmux_orchestrator import TmuxSession, TmuxWindow


class TestAgentMessengerInit:
    """Tests for AgentMessenger initialization."""

    def test_init_with_dependencies(self, tmp_path: Path) -> None:
        """Should initialize with orchestrator and store."""
        mock_orchestrator = MagicMock()
        conn = DatabaseConnection.from_path(tmp_path / "test.db")
        store = MessageStore(connection=conn)

        messenger = AgentMessenger(
            orchestrator=mock_orchestrator,
            store=store,
        )

        assert messenger.orchestrator is mock_orchestrator
        assert messenger.store is store


class TestAgentMessengerSend:
    """Tests for send method."""

    def test_send_stores_message(self, tmp_path: Path) -> None:
        """Should store message in SQLite."""
        mock_orchestrator = MagicMock()
        conn = DatabaseConnection.from_path(tmp_path / "test.db")
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="fork-s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = messenger.send(msg)

        assert result is True
        stored = store.get_for_agent("fork-s2:0")
        assert len(stored) == 1
        assert stored[0].id == msg.id

    def test_send_uses_discreet_signaling(self, tmp_path: Path) -> None:
        """Should use set-option as side-channel and avoid intrusive display-message."""
        mock_orchestrator = MagicMock()
        conn = DatabaseConnection.from_path(tmp_path / "test.db")
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="leader:0",
            to_agent="fork-worker:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "run"}',
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            # Mock current session to be different from target
            with patch.object(messenger, "_get_current_session", return_value="orchestrator"):
                messenger.send(msg)

            # Calls expected:
            # 1. has-session
            # 2. set-option (side-channel)
            # 3. display-message (alert)

            # Check for set-option call
            set_opt_call = next(
                (c for c in mock_run.call_args_list if "set-option" in c[0][0]), None
            )
            assert set_opt_call is not None
            assert "@last_fork_msg" in set_opt_call[0][0]

            # Check for display-message call (discreet)
            display_msg_call = next(
                (c for c in mock_run.call_args_list if "display-message" in c[0][0]), None
            )
            assert display_msg_call is not None
            assert "FORK: Msg from leader:0" in display_msg_call[0][0]

    def test_send_avoids_display_message_on_current_session(self, tmp_path: Path) -> None:
        """Should NOT show display-message if target is current session."""
        mock_orchestrator = MagicMock()
        conn = DatabaseConnection.from_path(tmp_path / "test.db")
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="orchestrator:0",
            to_agent="orchestrator:0",
            message_type=MessageType.COMMAND,
            payload="self message",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch.object(messenger, "_get_current_session", return_value="orchestrator"):
                messenger.send(msg)

            # Check that display-message was NOT called
            display_msg_calls = [c for c in mock_run.call_args_list if "display-message" in c[0][0]]
            assert len(display_msg_calls) == 0


class TestAgentMessengerBroadcast:
    """Tests for broadcast method."""

    def test_broadcast_to_all_sessions_excluding_self(self, tmp_path: Path) -> None:
        """Should send to all active agent sessions but skip current one."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_sessions.return_value = [
            TmuxSession(
                name="fork-agent1",
                windows=(
                    TmuxWindow(
                        session_name="fork-agent1", window_index=0, window_name="main", active=True
                    ),
                ),
                attached=False,
            ),
            TmuxSession(
                name="orchestrator",
                windows=(
                    TmuxWindow(
                        session_name="orchestrator", window_index=0, window_name="main", active=True
                    ),
                ),
                attached=False,
            ),
        ]
        conn = DatabaseConnection.from_path(tmp_path / "test.db")
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch.object(messenger, "_get_current_session", return_value="orchestrator"):
                count = messenger.broadcast(from_agent="orchestrator:0", payload="status update")

        # Should only send to fork-agent1
        assert count == 1
