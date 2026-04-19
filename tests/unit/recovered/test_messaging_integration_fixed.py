"""E2E tests for inter-agent messaging with real tmux.

These tests require tmux to be installed and available in PATH.
They create real tmux sessions and test the full messaging flow.
"""

from __future__ import annotations

import contextlib
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.messaging.agent_messenger import AgentMessenger, ALLOWED_SESSION_PREFIXES
from src.application.services.messaging.message_protocol import (
    FORK_MSG_PREFIX,
    FORK_MSG_SHORT_PREFIX,
    decode_message,
)
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.persistence.database import DatabaseConnection
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


# Check if tmux is available
def tmux_available() -> bool:
    """Check if tmux is installed and available."""
    try:
        result = subprocess.run(
            ["tmux", "-V"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# Skip all tests in this module if tmux is not available
pytestmark = pytest.mark.skipif(
    not tmux_available(),
    reason="tmux not available",
)


@pytest.fixture
def tmux_cleanup():
    """Cleanup tmux sessions created during tests."""
    sessions_to_cleanup = []

    yield sessions_to_cleanup.append

    # Cleanup: kill all test sessions
    for session_name in sessions_to_cleanup:
        with contextlib.suppress(subprocess.SubprocessError, subprocess.TimeoutExpired):
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                timeout=5,
            )


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_messages.db"


@pytest.fixture
def messenger(temp_db: Path) -> AgentMessenger:
    """Create an AgentMessenger with test configuration."""
    orchestrator = TmuxOrchestrator(safety_mode=False)
    conn = DatabaseConnection.from_path(temp_db)
    store = MessageStore(connection=conn)
    return AgentMessenger(orchestrator=orchestrator, store=store)


class TestTmuxSessionLifecycle:
    """Tests for tmux session creation and cleanup."""

    def test_create_and_list_session(self, tmux_cleanup, temp_db: Path) -> None:  # noqa: ARG002
        """Should create a tmux session and list it."""
        orchestrator = TmuxOrchestrator(safety_mode=False)

        # Create session
        session_name = "fork-test-e2e-session"
        success = orchestrator.create_session(session_name)
        tmux_cleanup(session_name)

        assert success, "Failed to create tmux session"

        # List sessions
        sessions = orchestrator.get_sessions()
        session_names = [s.name for s in sessions]

        assert session_name in session_names

    def test_kill_session(self, tmux_cleanup) -> None:  # noqa: ARG002
        """Should kill a tmux session."""
        orchestrator = TmuxOrchestrator(safety_mode=False)

        session_name = "fork-test-e2e-kill"
        orchestrator.create_session(session_name)

        # Verify it exists
        sessions = orchestrator.get_sessions()
        assert session_name in [s.name for s in sessions]

        # Kill it
        success = orchestrator.kill_session(session_name)
        assert success

        # Verify it's gone
        sessions = orchestrator.get_sessions()
        assert session_name not in [s.name for s in sessions]


class TestMessageSendAndCapture:
    """Tests for sending messages."""

    def test_send_message_to_session(self, tmux_cleanup, temp_db: Path) -> None:
        """Should send a message to a tmux session and store it."""
        orchestrator = TmuxOrchestrator(safety_mode=False)
        conn = DatabaseConnection.from_path(temp_db)
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=orchestrator, store=store)

        # Create session
        session_name = "fork-test-e2e-send"
        success = orchestrator.create_session(session_name)
        assert success, "Failed to create tmux session"
        tmux_cleanup(session_name)

        # Wait for session to be ready
        time.sleep(0.1)

        # Get the actual window index from the session
        sessions = orchestrator.get_sessions()
        target_session = next((s for s in sessions if s.name == session_name), None)
        assert target_session is not None, f"Session {session_name} not found"

        # Get first window index
        window_index = target_session.windows[0].window_index
        target_agent = f"{session_name}:{window_index}"

        # Create and send message
        msg = AgentMessage.create(
            from_agent="cli:0",
            to_agent=target_agent,
            message_type=MessageType.COMMAND,
            payload="test message e2e",
        )

        success = messenger.send(msg)
        assert success, f"Failed to send message to {target_agent}"

        # Verify it's stored
        messages = store.get_for_agent(target_agent)
        assert len(messages) == 1
        assert messages[0].payload == "test message e2e"


class TestMessageBroadcast:
    """Tests for broadcasting messages to all sessions."""

    def test_broadcast_includes_created_sessions(self, tmux_cleanup, temp_db: Path) -> None:
        """Should broadcast a message to our test sessions."""
        orchestrator = TmuxOrchestrator(safety_mode=False)
        conn = DatabaseConnection.from_path(temp_db)
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=orchestrator, store=store)

        # Create multiple sessions with valid prefixes
        prefix = ALLOWED_SESSION_PREFIXES[0]
        sessions = [
            f"{prefix}test-e2e-bc-1",
            f"{prefix}test-e2e-bc-2",
        ]
        for session_name in sessions:
            success = orchestrator.create_session(session_name)
            assert success, f"Failed to create session {session_name}"
            tmux_cleanup(session_name)

        time.sleep(0.1)

        # Broadcast message
        count = messenger.broadcast(
            from_agent="cli:0",
            payload="broadcast test message",
        )

        # Should send to at least our test sessions
        assert count >= 2, f"Expected at least 2 broadcasts, got {count}"

    def test_broadcast_stores_messages(self, tmux_cleanup, temp_db: Path) -> None:
        """Should store broadcast messages in the database."""
        orchestrator = TmuxOrchestrator(safety_mode=False)
        conn = DatabaseConnection.from_path(temp_db)
        store = MessageStore(connection=conn)
        
        # Create session
        session_name = "fork-test-e2e-bc-store"
        orchestrator.create_session(session_name)
        tmux_cleanup(session_name)

        time.sleep(0.1)

        # Get actual window index
        sessions = orchestrator.get_sessions()
        target_session = next((s for s in sessions if s.name == session_name), None)
        assert target_session is not None
        window_index = target_session.windows[0].window_index
        target_agent = f"{session_name}:{window_index}"

        messenger = AgentMessenger(orchestrator=orchestrator, store=store)

        # Broadcast
        count = messenger.broadcast(from_agent="cli:0", payload="stored broadcast")

        # At least one message should be sent
        assert count >= 1, "No broadcasts sent"

        # Check store has messages for our target
        messages = store.get_for_agent(target_agent)
        assert len(messages) >= 1, f"No messages stored for {target_agent}"


class TestMessageHistory:
    """Tests for message history functionality."""

    def test_history_includes_sent_and_received(self, tmux_cleanup, temp_db: Path) -> None:
        """History should include both sent and received messages."""
        orchestrator = TmuxOrchestrator(safety_mode=False)
        conn = DatabaseConnection.from_path(temp_db)
        store = MessageStore(connection=conn)
        messenger = AgentMessenger(orchestrator=orchestrator, store=store)

        # Create sessions
        session1 = "fork-test-e2e-hist1"
        session2 = "fork-test-e2e-hist2"
        orchestrator.create_session(session1)
        orchestrator.create_session(session2)
        tmux_cleanup(session1)
        tmux_cleanup(session2)

        time.sleep(0.1)

        # Send message from session1 to session2
        msg1 = AgentMessage.create(
            from_agent=f"{session1}:0",
            to_agent=f"{session2}:0",
            message_type=MessageType.COMMAND,
            payload="sent message",
        )
        messenger.send(msg1)

        # Send message from session2 to session1
        msg2 = AgentMessage.create(
            from_agent=f"{session2}:0",
            to_agent=f"{session1}:0",
            message_type=MessageType.REPLY,
            payload="reply message",
        )
        messenger.send(msg2)

        # Check history for session1
        history = messenger.get_history(f"{session1}:0")
        assert len(history) == 2

        payloads = {m.payload for m in history}
        assert "sent message" in payloads
        assert "reply message" in payloads
