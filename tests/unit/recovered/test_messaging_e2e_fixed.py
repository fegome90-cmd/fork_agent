"""E2E tests for messaging system with real tmux sessions.

These tests require tmux to be installed and will create/destroy
temporary tmux sessions.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from src.application.services.messaging.agent_messenger import AgentMessenger, ALLOWED_SESSION_PREFIXES
from src.application.services.messaging.message_protocol import (
    FORK_MSG_PREFIX,
    FORK_MSG_SHORT_PREFIX,
    FORK_MSG_TEMP_DIR,
    decode_message,
    encode_message,
)
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.persistence.database import DatabaseConnection
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


@pytest.fixture
def message_store(tmp_path: Path) -> MessageStore:
    """Create a MessageStore with a temporary database."""
    conn = DatabaseConnection.from_path(tmp_path / "messages.db")
    return MessageStore(connection=conn)


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
    prefix = ALLOWED_SESSION_PREFIXES[0]
    session_name = f"{prefix}test-msg-{int(time.time() * 1000)}"

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
        target_agent = f"{tmux_session}:0"
        msg = AgentMessage.create(
            from_agent="cli:0",
            to_agent=target_agent,
            message_type=MessageType.COMMAND,
            payload="test message",
        )

        agent_messenger.send(msg)

        # Verify stored
        stored = message_store.get_for_agent(target_agent)
        assert len(stored) == 1
        assert stored[0].payload == "test message"

    def test_send_via_tmux_send_keys_legacy(
        self,
        tmux_session: str,
    ) -> None:
        """Verify we can still detect legacy full-prefix messages."""
        import json
        json_data = {
            "id": "legacy-id",
            "from_agent": "test:0",
            "to_agent": f"{tmux_session}:0",
            "message_type": "COMMAND",
            "payload": "hello legacy",
            "created_at": 12345
        }
        encoded = f"{FORK_MSG_PREFIX} {json.dumps(json_data)}"

        # Send via tmux
        subprocess.run(["tmux", "send-keys", "-t", tmux_session, encoded], capture_output=True)
        subprocess.run(["tmux", "send-keys", "-t", tmux_session, "Enter"], capture_output=True)

        time.sleep(0.1)

        # Capture content
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", tmux_session, "-p", "-S", "-50"],
            capture_output=True,
            text=True,
        )

        assert FORK_MSG_PREFIX in result.stdout
        assert "hello legacy" in result.stdout

    def test_message_history(
        self,
        agent_messenger: AgentMessenger,
        message_store: MessageStore,
        tmux_session: str,
    ) -> None:
        """History should show both sent and received messages."""
        target_agent = f"{tmux_session}:0"
        # Send a message
        msg1 = AgentMessage.create(
            from_agent="cli:0",
            to_agent=target_agent,
            message_type=MessageType.COMMAND,
            payload="outgoing",
        )
        agent_messenger.send(msg1)

        # Simulate a reply
        msg2 = AgentMessage.create(
            from_agent=target_agent,
            to_agent="cli:0",
            message_type=MessageType.REPLY,
            payload="incoming",
        )
        message_store.save(msg2)

        # Get history for the session
        history = agent_messenger.get_history(target_agent)

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
        db_path = message_store._connection._config.db_path
        conn = sqlite3.connect(str(db_path))
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
    """End-to-end tests for message protocol with real tmux capture."""

    def test_encode_produces_valid_json_in_file(self, tmp_path: Path) -> None:
        """Encoded message should write valid JSON to file."""
        import json
        from unittest.mock import patch

        msg = AgentMessage.create(
            from_agent="sender:0",
            to_agent="receiver:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "test"}',
            correlation_id="req-123",
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encoded = encode_message(msg)
            assert encoded.startswith(FORK_MSG_SHORT_PREFIX)
            
            temp_file = tmp_path / f"fork_msg_{msg.id[:8]}.json"
            assert temp_file.exists()
            
            data = json.loads(temp_file.read_text())
            assert data["from_agent"] == "sender:0"

    def test_decode_from_tmux_capture_v2(
        self,
        tmux_session: str,
        tmp_path: Path
    ) -> None:
        """Decode a v2 message that was sent to tmux and captured back."""
        from unittest.mock import patch
        
        original = AgentMessage.create(
            from_agent="sender:0",
            to_agent=f"{tmux_session}:0",
            message_type=MessageType.COMMAND,
            payload="test payload for v2",
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encoded = encode_message(original)

            # Send to tmux
            subprocess.run(["tmux", "send-keys", "-t", tmux_session, encoded], capture_output=True)
            subprocess.run(["tmux", "send-keys", "-t", tmux_session, "Enter"], capture_output=True)

            time.sleep(0.1)

            # Capture from tmux
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", tmux_session, "-p", "-S", "-100"],
                capture_output=True,
                text=True,
            )

            # Decode using the same temp dir
            decoded = decode_message(result.stdout)
            
            assert decoded is not None
            assert decoded.id == original.id
            assert decoded.payload == "test payload for v2"
