"""Tests for domain message entity."""

from __future__ import annotations

import time

import pytest

from src.domain.entities.message import AgentMessage, MessageType


class TestMessageType:
    """Tests for MessageType enum."""

    def test_has_command_type(self) -> None:
        """MessageType should have COMMAND."""
        assert hasattr(MessageType, "COMMAND")

    def test_has_reply_type(self) -> None:
        """MessageType should have REPLY."""
        assert hasattr(MessageType, "REPLY")

    def test_has_handoff_type(self) -> None:
        """MessageType should have HANDOFF."""
        assert hasattr(MessageType, "HANDOFF")

    def test_has_exactly_six_types(self) -> None:
        """MessageType should have exactly 6 types."""
        types = list(MessageType)
        assert len(types) == 6
        assert MessageType.COMMAND in types
        assert MessageType.REPLY in types
        assert MessageType.HANDOFF in types
        assert MessageType.PROGRESS in types
        assert MessageType.FILE_TOUCHED in types
        assert MessageType.OBSERVATION in types


class TestAgentMessage:
    """Tests for AgentMessage dataclass."""

    def test_create_basic_message(self) -> None:
        """Should create a basic message with required fields."""
        msg = AgentMessage.create(
            from_agent="session1:0",
            to_agent="session2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "analyze"}',
        )

        assert msg.from_agent == "session1:0"
        assert msg.to_agent == "session2:0"
        assert msg.message_type == MessageType.COMMAND
        assert msg.payload == '{"task": "analyze"}'
        assert msg.id  # Should have UUID
        assert msg.created_at > 0  # Should have timestamp in ms
        assert msg.correlation_id is None

    def test_create_message_with_correlation_id(self) -> None:
        """Should create message with correlation_id for request/response matching."""
        correlation = "req-123"
        msg = AgentMessage.create(
            from_agent="session1:0",
            to_agent="session2:0",
            message_type=MessageType.REPLY,
            payload='{"result": "ok"}',
            correlation_id=correlation,
        )

        assert msg.correlation_id == correlation

    def test_broadcast_message_uses_star(self) -> None:
        """Broadcast messages use to_agent='*'."""
        msg = AgentMessage.create(
            from_agent="session1:0",
            to_agent="*",
            message_type=MessageType.COMMAND,
            payload='{"status": "heartbeat"}',
        )

        assert msg.to_agent == "*"

    def test_message_is_immutable(self) -> None:
        """AgentMessage should be frozen (immutable)."""
        msg = AgentMessage.create(
            from_agent="session1:0",
            to_agent="session2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        with pytest.raises(AttributeError):
            msg.payload = "modified"  # type: ignore[misc]

    def test_message_has_unique_ids(self) -> None:
        """Each message should have a unique ID."""
        msg1 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test1",
        )
        msg2 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test2",
        )

        assert msg1.id != msg2.id

    def test_timestamp_is_milliseconds(self) -> None:
        """Timestamp should be in milliseconds."""
        before = int(time.time() * 1000)
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )
        after = int(time.time() * 1000)

        assert before <= msg.created_at <= after

    def test_direct_instantiation(self) -> None:
        """Should allow direct instantiation with all fields."""
        msg = AgentMessage(
            id="test-id-123",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="direct",
            created_at=1234567890000,
            correlation_id="corr-123",
        )

        assert msg.id == "test-id-123"
        assert msg.from_agent == "s1:0"
        assert msg.to_agent == "s2:0"
        assert msg.message_type == MessageType.COMMAND
        assert msg.payload == "direct"
        assert msg.created_at == 1234567890000
        assert msg.correlation_id == "corr-123"

    def test_optional_correlation_id_is_none(self) -> None:
        """correlation_id should default to None."""
        msg = AgentMessage(
            id="test-id",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
            created_at=1234567890000,
        )

        assert msg.correlation_id is None
