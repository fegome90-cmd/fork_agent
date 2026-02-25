"""Tests for AgentMessenger service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.application.services.messaging.message_protocol import FORK_MSG_PREFIX
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.tmux_orchestrator import TmuxSession, TmuxWindow


class TestAgentMessengerInit:
    """Tests for AgentMessenger initialization."""

    def test_init_with_dependencies(self, tmp_path: Path) -> None:
        """Should initialize with orchestrator and store."""
        mock_orchestrator = MagicMock()
        store = MessageStore(db_path=tmp_path / "test.db")

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
        mock_orchestrator.send_message.return_value = True
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        result = messenger.send(msg)

        assert result is True
        stored = store.get_for_agent("s2:0")
        assert len(stored) == 1
        assert stored[0].id == msg.id

    def test_send_uses_tmux_send_keys(self, tmp_path: Path) -> None:
        """Should send message via tmux send-keys."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.send_message.return_value = True
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="leader:0",
            to_agent="worker:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "run"}',
        )

        messenger.send(msg)

        # Should call send_message with session:window from to_agent
        mock_orchestrator.send_message.assert_called_once()
        call_args = mock_orchestrator.send_message.call_args
        assert call_args[0][0] == "worker"  # session
        assert call_args[0][1] == 0  # window

    def test_send_returns_false_on_tmux_failure(self, tmp_path: Path) -> None:
        """Should return False if tmux send fails."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.send_message.return_value = False
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        result = messenger.send(msg)

        assert result is False

    def test_send_stores_even_on_tmux_failure(self, tmp_path: Path) -> None:
        """Should store message even if tmux send fails (for retry/audit)."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.send_message.return_value = False
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        messenger.send(msg)

        stored = store.get_for_agent("s2:0")
        assert len(stored) == 1  # Still stored for audit/retry

    def test_send_encodes_message_with_protocol(self, tmp_path: Path) -> None:
        """Should encode message using protocol prefix."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.send_message.return_value = True
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        messenger.send(msg)

        call_args = mock_orchestrator.send_message.call_args
        message_content = call_args[0][2]  # Third arg is the message
        assert message_content.startswith(FORK_MSG_PREFIX)


class TestAgentMessengerBroadcast:
    """Tests for broadcast method."""

    def test_broadcast_to_all_sessions(self, tmp_path: Path) -> None:
        """Should send to all active sessions."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.send_message.return_value = True
        mock_orchestrator.get_sessions.return_value = [
            TmuxSession(
                name="agent1",
                windows=(
                    TmuxWindow(
                        session_name="agent1", window_index=0, window_name="main", active=True
                    ),
                ),
                attached=False,
            ),
            TmuxSession(
                name="agent2",
                windows=(
                    TmuxWindow(
                        session_name="agent2", window_index=0, window_name="main", active=True
                    ),
                ),
                attached=False,
            ),
            TmuxSession(
                name="agent3",
                windows=(
                    TmuxWindow(
                        session_name="agent3", window_index=0, window_name="main", active=True
                    ),
                ),
                attached=False,
            ),
        ]
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        count = messenger.broadcast(from_agent="leader:0", payload="status update")

        assert count == 3
        assert mock_orchestrator.send_message.call_count == 3

    def test_broadcast_uses_star_target(self, tmp_path: Path) -> None:
        """Broadcast should store messages for each target."""
        from src.infrastructure.tmux_orchestrator import TmuxSession, TmuxWindow

        mock_orchestrator = MagicMock()
        mock_orchestrator.send_message.return_value = True

        # Create proper TmuxWindow and TmuxSession objects
        window = TmuxWindow(session_name="agent1", window_index=0, window_name="main", active=True)
        session = TmuxSession(name="agent1", windows=(window,), attached=False)
        mock_orchestrator.get_sessions.return_value = [session]

        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        messenger.broadcast(from_agent="leader:0", payload="update")

        # Check stored message - broadcast creates messages with actual targets
        stored = store.get_for_agent("agent1:0")
        assert len(stored) == 1
        assert stored[0].to_agent == "agent1:0"

    def test_broadcast_returns_count_of_successful_sends(self, tmp_path: Path) -> None:
        """Should return count of successful sends."""
        mock_orchestrator = MagicMock()
        # Simulate some failures
        mock_orchestrator.send_message.side_effect = [True, False, True]
        mock_orchestrator.get_sessions.return_value = [
            MagicMock(name="agent1", windows=[MagicMock(window_index=0)]),
            MagicMock(name="agent2", windows=[MagicMock(window_index=0)]),
            MagicMock(name="agent3", windows=[MagicMock(window_index=0)]),
        ]
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        count = messenger.broadcast(from_agent="leader:0", payload="update")

        assert count == 2  # Only 2 succeeded


class TestAgentMessengerGetMessages:
    """Tests for get_messages method."""

    def test_get_messages_delegates_to_store(self, tmp_path: Path) -> None:
        """Should delegate to store.get_for_agent."""
        mock_orchestrator = MagicMock()
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        # Add some messages
        msg1 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="msg1",
        )
        msg2 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="msg2",
        )
        store.save(msg1)
        store.save(msg2)

        messages = messenger.get_messages("s2:0")

        assert len(messages) == 2

    def test_get_messages_respects_limit(self, tmp_path: Path) -> None:
        """Should respect limit parameter."""
        mock_orchestrator = MagicMock()
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        for i in range(10):
            msg = AgentMessage.create(
                from_agent="s1:0",
                to_agent="s2:0",
                message_type=MessageType.COMMAND,
                payload=f"msg{i}",
            )
            store.save(msg)

        messages = messenger.get_messages("s2:0", limit=5)

        assert len(messages) == 5


class TestAgentMessengerGetHistory:
    """Tests for get_history method."""

    def test_get_history_delegates_to_store(self, tmp_path: Path) -> None:
        """Should delegate to store.get_history."""
        mock_orchestrator = MagicMock()
        store = MessageStore(db_path=tmp_path / "test.db")
        messenger = AgentMessenger(orchestrator=mock_orchestrator, store=store)

        # Add sent and received messages
        sent = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="sent",
        )
        received = AgentMessage.create(
            from_agent="s2:0",
            to_agent="s1:0",
            message_type=MessageType.REPLY,
            payload="received",
        )
        store.save(sent)
        store.save(received)

        history = messenger.get_history("s1:0")

        assert len(history) == 2
        payloads = {m.payload for m in history}
        assert "sent" in payloads
        assert "received" in payloads
