"""Tests for message protocol encoding/decoding."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.application.services.messaging.message_protocol import (
    FORK_MSG_PREFIX,
    FORK_MSG_SHORT_PREFIX,
    FORK_MSG_TEMP_DIR,
    create_command,
    create_handoff,
    create_reply,
    decode_message,
    encode_message,
)
from src.domain.entities.message import AgentMessage, MessageType


class TestForkMsgPrefix:
    """Tests for protocol prefix constants."""

    def test_prefixes_are_defined(self) -> None:
        """Prefixes should be defined with comment prefix for shell safety."""
        assert FORK_MSG_PREFIX == "# FORK_MSG:"
        assert FORK_MSG_SHORT_PREFIX == "# F:"

    def test_prefixes_end_with_colon(self) -> None:
        """Prefixes should end with colon for easy splitting."""
        assert FORK_MSG_PREFIX.endswith(":")
        assert FORK_MSG_SHORT_PREFIX.endswith(":")


class TestEncodeMessage:
    """Tests for encode_message function."""

    def test_encode_basic_message(self, tmp_path: Path) -> None:
        """Should encode message with short prefix."""
        msg = AgentMessage(
            id="test-id-long-enough",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "run"}',
            created_at=1234567890000,
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encoded = encode_message(msg)

            assert encoded.startswith(FORK_MSG_SHORT_PREFIX)
            assert msg.id[:8] in encoded
            
            # Should have created a temp file
            temp_file = tmp_path / f"fork_msg_{msg.id[:8]}.json"
            assert temp_file.exists()

    def test_encode_produces_valid_json_in_file(self, tmp_path: Path) -> None:
        """Encoded message in temp file should be valid JSON."""
        msg = AgentMessage(
            id="test-id-long-enough",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test payload",
            created_at=1234567890000,
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encode_message(msg)
            temp_file = tmp_path / f"fork_msg_{msg.id[:8]}.json"
            
            data = json.loads(temp_file.read_text())
            assert data["id"] == "test-id-long-enough"

    def test_encode_includes_all_fields(self, tmp_path: Path) -> None:
        """Encoded message in file should include all message fields."""
        msg = AgentMessage(
            id="msg-123-long-enough",
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.REPLY,
            payload='{"result": "success"}',
            created_at=9999999999999,
            correlation_id="corr-456",
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encode_message(msg)
            temp_file = tmp_path / f"fork_msg_{msg.id[:8]}.json"
            data = json.loads(temp_file.read_text())

            assert data["id"] == "msg-123-long-enough"
            assert data["from_agent"] == "agent1:0"
            assert data["to_agent"] == "agent2:0"
            assert data["message_type"] == "REPLY"
            assert data["payload"] == '{"result": "success"}'
            assert data["created_at"] == 9999999999999
            assert data["correlation_id"] == "corr-456"


class TestDecodeMessage:
    """Tests for decode_message function."""

    def test_decode_valid_message_v2(self, tmp_path: Path) -> None:
        """Should decode a valid v2 encoded message (from file)."""
        msg = AgentMessage(
            id="test-id-12345",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "go"}',
            created_at=1234567890000,
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encoded = encode_message(msg)
            decoded = decode_message(encoded)

            assert decoded is not None
            assert decoded.id == msg.id
            assert decoded.payload == msg.payload

    def test_decode_valid_message_v1(self) -> None:
        """Should decode a valid v1 encoded message (fallback)."""
        json_data = {
            "id": "v1-id",
            "from_agent": "s:0",
            "to_agent": "s:1",
            "message_type": "COMMAND",
            "payload": "p",
            "created_at": 123
        }
        encoded = f"{FORK_MSG_PREFIX} {json.dumps(json_data)}"
        decoded = decode_message(encoded)

        assert decoded is not None
        assert decoded.id == "v1-id"

    def test_decode_returns_none_for_invalid_prefix(self) -> None:
        """Should return None if prefix is missing."""
        result = decode_message("INVALID: some data")
        assert result is None

    def test_decode_returns_none_for_invalid_json_v1(self) -> None:
        """Should return None if v1 JSON is malformed."""
        result = decode_message(f"{FORK_MSG_PREFIX} not valid json")
        assert result is None

    def test_decode_returns_none_for_missing_fields_v1(self) -> None:
        """Should return None if required fields are missing in v1."""
        result = decode_message(f'{FORK_MSG_PREFIX} {{"id": "test"}}')
        assert result is None


class TestCreateCommand:
    """Tests for create_command helper."""

    def test_creates_command_message(self) -> None:
        """Should create a COMMAND type message."""
        msg = create_command(
            from_="leader:0",
            to="worker:0",
            command="run_task",
        )

        assert msg.message_type == MessageType.COMMAND
        assert msg.from_agent == "leader:0"
        assert msg.to_agent == "worker:0"

    def test_payload_is_json_with_command(self) -> None:
        """Payload should be JSON with command field."""
        msg = create_command(
            from_="leader:0",
            to="worker:0",
            command="analyze",
        )

        data = json.loads(msg.payload)
        assert data["command"] == "analyze"


class TestCreateReply:
    """Tests for create_reply helper."""

    def test_creates_reply_message(self) -> None:
        """Should create a REPLY type message."""
        msg = create_reply(
            from_="worker:0",
            to="leader:0",
            correlation_id="req-123",
            response="task completed",
        )

        assert msg.message_type == MessageType.REPLY
        assert msg.from_agent == "worker:0"
        assert msg.to_agent == "leader:0"
        assert msg.correlation_id == "req-123"


class TestCreateHandoff:
    """Tests for create_handoff helper."""

    def test_creates_handoff_message(self) -> None:
        """Should create a HANDOFF type message."""
        msg = create_handoff(
            from_="agent1:0",
            to="agent2:0",
            handoff_path="/work/context.md",
        )

        assert msg.message_type == MessageType.HANDOFF
        assert msg.from_agent == "agent1:0"
        assert msg.to_agent == "agent2:0"


class TestRoundTrip:
    """Tests for encode/decode round trip."""

    @pytest.mark.parametrize(
        "msg_type,payload",
        [
            (MessageType.COMMAND, '{"task": "run"}'),
            (MessageType.REPLY, '{"result": "ok"}'),
            (MessageType.HANDOFF, '{"handoff_path": "/ctx.md"}'),
        ],
    )
    def test_round_trip_preserves_message(self, msg_type: MessageType, payload: str, tmp_path: Path) -> None:
        """Encode/decode should preserve message data using v2."""
        original = AgentMessage(
            id="test-id-round-trip",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=msg_type,
            payload=payload,
            created_at=1234567890000,
            correlation_id="corr-123",
        )

        with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
            encoded = encode_message(original)
            decoded = decode_message(encoded)

            assert decoded is not None
            assert decoded.id == original.id
            assert decoded.from_agent == original.from_agent
            assert decoded.to_agent == original.to_agent
            assert decoded.message_type == original.message_type
            assert decoded.payload == original.payload
            assert decoded.created_at == original.created_at
            assert decoded.correlation_id == original.correlation_id
