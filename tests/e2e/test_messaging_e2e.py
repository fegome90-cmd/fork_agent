"""E2E tests for messaging system with real tmux sessions.

These tests require tmux to be installed and will create/destroy
temporary tmux sessions.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.application.services.messaging.message_protocol import (
    FORK_MSG_PREFIX,
    encode_message,
)
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


@pytest.fixture
def message_store(tmp_path: Path) -> MessageStore:
    """Create a MessageStore with a temporary database."""
    return MessageStore(db_path=tmp_path / "messages.db")


@pytest.fixture
def tmux_orchestrator() -> TmuxOrchestrator:
    """Create a TmuxOrchestrator instance."""
    return TmuxOrchestrator(safety_mode=False)


@pytest.fixture
def agent_messenger(
    tmux_orchestrator: TmuxOrchestrator,
    message_store: MessageStore,
) -> AgentMessenger:
    """Create an AgentMessenger with test dependencies."""
    return AgentMessenger(
        orchestrator=tmux_orchestrator,
        store=message_store,
    )


@pytest.fixture
def tmux_session() -> str:
    """Create a temporary tmux session for testing.

    Yields the session name and cleans up after the test.
    Uses wide dimensions to prevent line wrapping in message tests.
    """
    session_name = f"test_msg_{int(time.time() * 1000)}"

    # Create session with wide dimensions to prevent line wrapping
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-x", "200", "-y", "20"],
        capture_output=True,
    )

    if result.returncode != 0:
        pytest.skip("tmux not available or session creation failed")

    yield session_name

    # Cleanup
    subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        capture_output=True,
    )


class TestMessagingE2E:
    """E2E tests for messaging with real tmux."""

    def test_tmux_session_available(self, tmux_session: str) -> None:
        """Verify tmux session fixture works."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", tmux_session],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_send_message_stores_in_db(
        self,
        agent_messenger: AgentMessenger,
        message_store: MessageStore,
        tmux_session: str,
    ) -> None:
        """Sending a message should store it in the database."""
        msg = AgentMessage.create(
            from_agent="cli:0",
            to_agent=f"{tmux_session}:0",
            message_type=MessageType.COMMAND,
            payload="test message",
        )

        agent_messenger.send(msg)

        # Verify stored
        stored = message_store.get_for_agent(f"{tmux_session}:0")
        assert len(stored) == 1
        assert stored[0].payload == "test message"

    def test_send_via_tmux_send_keys(
        self,
        tmux_session: str,
    ) -> None:
        """Verify we can send a message via tmux send-keys."""
        msg = AgentMessage.create(
            from_agent="test:0",
            to_agent=f"{tmux_session}:0",
            message_type=MessageType.COMMAND,
            payload="hello world",
        )

        encoded = encode_message(msg)

        # Send via tmux (use session name without window index)
        result = subprocess.run(
            ["tmux", "send-keys", "-t", tmux_session, encoded],
            capture_output=True,
        )
        assert result.returncode == 0

        # Press Enter
        result = subprocess.run(
            ["tmux", "send-keys", "-t", tmux_session, "Enter"],
            capture_output=True,
        )
        assert result.returncode == 0

        # Wait for tmux to process
        time.sleep(0.2)

        # Capture content
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", tmux_session, "-p", "-S", "-50"],
            capture_output=True,
            text=True,
        )

        assert FORK_MSG_PREFIX in result.stdout
        assert "hello world" in result.stdout

    def test_message_history(
        self,
        agent_messenger: AgentMessenger,
        message_store: MessageStore,
        tmux_session: str,
    ) -> None:
        """History should show both sent and received messages."""
        # Send a message
        msg1 = AgentMessage.create(
            from_agent="cli:0",
            to_agent=f"{tmux_session}:0",
            message_type=MessageType.COMMAND,
            payload="outgoing",
        )
        agent_messenger.send(msg1)

        # Simulate a reply
        msg2 = AgentMessage.create(
            from_agent=f"{tmux_session}:0",
            to_agent="cli:0",
            message_type=MessageType.REPLY,
            payload="incoming",
        )
        message_store.save(msg2)

        # Get history for the session
        history = agent_messenger.get_history(f"{tmux_session}:0")

        assert len(history) == 2
        payloads = {m.payload for m in history}
        assert "outgoing" in payloads
        assert "incoming" in payloads

    def test_message_cleanup_expired(
        self,
        message_store: MessageStore,
    ) -> None:
        """Expired messages should be cleaned up."""
        import sqlite3

        # Create a message
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )
        message_store.save(msg)

        # Manually expire it
        conn = sqlite3.connect(str(message_store.get_db_path()))
        conn.execute("UPDATE messages SET expires_at = 0")
        conn.commit()
        conn.close()

        # Cleanup
        removed = message_store.cleanup_expired()

        assert removed == 1

        # Verify gone
        remaining = message_store.get_for_agent("s2:0")
        assert len(remaining) == 0


class TestMessageProtocolE2E:
    """E2E tests for message protocol with real tmux capture."""

    def test_encode_produces_valid_json(self) -> None:
        """Encoded message should be valid JSON after prefix."""
        import json

        msg = AgentMessage.create(
            from_agent="sender:0",
            to_agent="receiver:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "test"}',
            correlation_id="req-123",
        )

        encoded = encode_message(msg)
        json_part = encoded[len(FORK_MSG_PREFIX) :]

        # Should parse as valid JSON
        data = json.loads(json_part)
        assert data["from_agent"] == "sender:0"
        assert data["correlation_id"] == "req-123"

    def test_decode_from_tmux_capture(
        self,
        tmux_session: str,
    ) -> None:
        """Decode a message that was sent to tmux and captured back."""
        original = AgentMessage.create(
            from_agent="sender:0",
            to_agent=f"{tmux_session}:0",
            message_type=MessageType.COMMAND,
            payload="test payload for decode",
        )

        encoded = encode_message(original)

        # Send to tmux (use session name without window index)
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_session, encoded],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_session, "Enter"],
            capture_output=True,
            check=True,
        )

        time.sleep(0.2)

        # Capture from tmux
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", tmux_session, "-p", "-S", "-100"],
            capture_output=True,
            text=True,
        )

        content = result.stdout

        # Just verify the message is in the output
        # (Full decode test is in unit tests - this is just E2E verification)
        assert FORK_MSG_PREFIX in content
        assert "sender:0" in content
        assert "test payload for decode" in content
