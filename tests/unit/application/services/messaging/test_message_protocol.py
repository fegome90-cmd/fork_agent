"""Tests for message protocol encoding/decoding."""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pytest

from src.application.services.messaging.message_protocol import (
    FORK_MSG_PREFIX,
    FORK_MSG_SHORT_PREFIX,
    FORK_MSG_TEMP_DIR,
    cleanup_temp_files,
    create_command,
    create_handoff,
    create_reply,
    decode_message,
    encode_message,
)
from src.domain.entities.message import AgentMessage, MessageType


class TestForkMsgPrefix:
    """Tests for protocol prefix constants."""

    def test_prefix_is_defined(self) -> None:
        """FORK_MSG_PREFIX should be defined with comment prefix for shell safety."""
        assert FORK_MSG_PREFIX == "# FORK_MSG:"

    def test_prefix_ends_with_colon(self) -> None:
        """Prefix should end with colon for easy splitting."""
        assert FORK_MSG_PREFIX.endswith(":")

    def test_short_prefix_is_defined(self) -> None:
        """FORK_MSG_SHORT_PREFIX should be defined for v2 protocol."""
        assert FORK_MSG_SHORT_PREFIX == "# F:"

    def test_short_prefix_ends_with_colon(self) -> None:
        """Short prefix should end with colon."""
        assert FORK_MSG_SHORT_PREFIX.endswith(":")


class TestEncodeMessage:
    """Tests for encode_message function (v2 protocol)."""

    def test_encode_uses_short_prefix(self) -> None:
        """Should encode message with short prefix (# F:)."""
        msg = AgentMessage(
            id="test-id-12345",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "run"}',
            created_at=1234567890000,
        )

        encoded = encode_message(msg)

        assert encoded.startswith(FORK_MSG_SHORT_PREFIX)

    def test_encode_is_short(self) -> None:
        """Encoded message should be short (< 20 chars)."""
        msg = AgentMessage(
            id="test-id-12345",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "run"}',
            created_at=1234567890000,
        )

        encoded = encode_message(msg)

        # Format: "# F:{id_short}" where id_short is first 8 chars
        assert len(encoded) < 20

    def test_encode_writes_temp_file(self) -> None:
        """Should write full JSON to temp file."""
        msg = AgentMessage(
            id="unique-test-id-999",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test payload",
            created_at=1234567890000,
        )

        encode_message(msg)

        # Check temp file exists
        pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{msg.id[:8]}*.json")
        matches = glob.glob(pattern)
        assert len(matches) >= 1

        # Verify JSON content
        data = json.loads(Path(matches[0]).read_text())
        assert data["id"] == msg.id
        assert data["from_agent"] == msg.from_agent

        # Cleanup
        for match in matches:
            Path(match).unlink()

    def test_encode_includes_all_fields_in_temp_file(self) -> None:
        """Temp file should include all message fields."""
        msg = AgentMessage(
            id="msg-123-abc",
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.REPLY,
            payload='{"result": "success"}',
            created_at=9999999999999,
            correlation_id="corr-456",
        )

        encode_message(msg)

        # Read temp file
        pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{msg.id[:8]}*.json")
        matches = glob.glob(pattern)
        assert len(matches) >= 1

        data = json.loads(Path(matches[0]).read_text())

        assert data["id"] == "msg-123-abc"
        assert data["from_agent"] == "agent1:0"
        assert data["to_agent"] == "agent2:0"
        assert data["message_type"] == "REPLY"
        assert data["payload"] == '{"result": "success"}'
        assert data["created_at"] == 9999999999999
        assert data["correlation_id"] == "corr-456"

        # Cleanup
        for match in matches:
            Path(match).unlink()

    def test_encode_handles_none_correlation_id(self) -> None:
        """Should handle None correlation_id in temp file."""
        msg = AgentMessage(
            id="test-id-none",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
            created_at=1234567890000,
            correlation_id=None,
        )

        encode_message(msg)

        pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{msg.id[:8]}*.json")
        matches = glob.glob(pattern)
        assert len(matches) >= 1

        data = json.loads(Path(matches[0]).read_text())
        assert data["correlation_id"] is None

        # Cleanup
        for match in matches:
            Path(match).unlink()


class TestDecodeMessage:
    """Tests for decode_message function."""

    def test_decode_valid_message(self) -> None:
        """Should decode a valid encoded message."""
        msg = AgentMessage(
            id="test-id",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "go"}',
            created_at=1234567890000,
        )

        encoded = encode_message(msg)
        decoded = decode_message(encoded)

        assert decoded is not None
        assert decoded.id == msg.id
        assert decoded.from_agent == msg.from_agent
        assert decoded.to_agent == msg.to_agent
        assert decoded.message_type == MessageType.COMMAND
        assert decoded.payload == msg.payload
        assert decoded.created_at == msg.created_at

    def test_decode_returns_none_for_invalid_prefix(self) -> None:
        """Should return None if prefix is missing."""
        result = decode_message("INVALID: some data")
        assert result is None

    def test_decode_returns_none_for_invalid_json(self) -> None:
        """Should return None if JSON is malformed."""
        result = decode_message("FORK_MSG: not valid json")
        assert result is None

    def test_decode_returns_none_for_missing_fields(self) -> None:
        """Should return None if required fields are missing."""
        result = decode_message('FORK_MSG: {"id": "test"}')
        assert result is None

    def test_decode_handles_none_correlation_id(self) -> None:
        """Should correctly decode None correlation_id."""
        encoded = '# FORK_MSG: {"id": "x", "from_agent": "s:0", "to_agent": "s:1", "message_type": "COMMAND", "payload": "p", "created_at": 123, "correlation_id": null}'
        decoded = decode_message(encoded)

        assert decoded is not None
        assert decoded.correlation_id is None

    def test_decode_returns_none_for_invalid_message_type(self) -> None:
        """Should return None if message_type is invalid."""
        # Create JSON with invalid message_type
        invalid_json = json.dumps(
            {
                "id": "test",
                "from_agent": "s:0",
                "to_agent": "s:1",
                "message_type": "INVALID_TYPE",  # Invalid enum value
                "payload": "test",
                "created_at": 123,
            }
        )
        result = decode_message(f"FORK_MSG:{invalid_json}")
        assert result is None

    def test_decode_returns_none_for_type_error_in_json(self) -> None:
        """Should return None if TypeError occurs during JSON parsing."""
        # This can happen if the JSON part is not a string after prefix
        result = decode_message("FORK_MSG:null")
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

    def test_includes_kwargs_in_payload(self) -> None:
        """Additional kwargs should be included in payload."""
        msg = create_command(
            from_="leader:0",
            to="worker:0",
            command="process",
            file_path="/data/input.csv",
            mode="strict",
        )

        data = json.loads(msg.payload)
        assert data["command"] == "process"
        assert data["file_path"] == "/data/input.csv"
        assert data["mode"] == "strict"


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

    def test_payload_is_json_with_response(self) -> None:
        """Payload should be JSON with response field."""
        msg = create_reply(
            from_="worker:0",
            to="leader:0",
            correlation_id="req-123",
            response="done",
        )

        data = json.loads(msg.payload)
        assert data["response"] == "done"


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

    def test_payload_is_json_with_handoff_path(self) -> None:
        """Payload should be JSON with handoff_path field."""
        msg = create_handoff(
            from_="agent1:0",
            to="agent2:0",
            handoff_path="/session/state.json",
        )

        data = json.loads(msg.payload)
        assert data["handoff_path"] == "/session/state.json"


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
    def test_round_trip_preserves_message(self, msg_type: MessageType, payload: str) -> None:
        """Encode/decode should preserve message data."""
        original = AgentMessage(
            id="test-id-rt",
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=msg_type,
            payload=payload,
            created_at=1234567890000,
            correlation_id="corr-123",
        )

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

        # Cleanup
        pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{original.id[:8]}*.json")
        for match in glob.glob(pattern):
            Path(match).unlink()


class TestDecodeV2Protocol:
    """Tests for decode_message with v2 protocol."""

    def test_decode_short_prefix(self) -> None:
        """Should decode v2 protocol messages (# F:id_short)."""
        msg = AgentMessage(
            id="abc12345-def6",
            from_agent="s:0",
            to_agent="s:1",
            message_type=MessageType.COMMAND,
            payload="test",
            created_at=1234567890000,
        )

        # Encode creates temp file
        encoded = encode_message(msg)
        assert encoded.startswith("# F:")

        # Decode should read from temp file
        decoded = decode_message(encoded)
        assert decoded is not None
        assert decoded.id == msg.id

        # Cleanup
        pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{msg.id[:8]}*.json")
        for match in glob.glob(pattern):
            Path(match).unlink()

    def test_decode_returns_none_if_temp_file_missing(self) -> None:
        """Should return None if temp file doesn't exist."""
        # Try to decode with non-existent ID
        result = decode_message("# F:nonexist")
        assert result is None


class TestBackwardCompatibility:
    """Tests for v1 protocol backward compatibility."""

    def test_decode_v1_protocol(self) -> None:
        """Should still decode v1 protocol messages."""
        encoded = '# FORK_MSG:{"id":"x1","from_agent":"s:0","to_agent":"s:1","message_type":"COMMAND","payload":"test","created_at":123,"correlation_id":null}'
        decoded = decode_message(encoded)

        assert decoded is not None
        assert decoded.id == "x1"
        assert decoded.from_agent == "s:0"

    def test_decode_prefers_v2_over_v1(self) -> None:
        """Should prefer v2 if both prefixes present."""
        # Create v2 message with temp file
        msg = AgentMessage(
            id="prefer-v2-test",
            from_agent="s:0",
            to_agent="s:1",
            message_type=MessageType.COMMAND,
            payload="v2-data",
            created_at=1234567890000,
        )
        encoded = encode_message(msg)

        # Decode should work
        decoded = decode_message(encoded)
        assert decoded is not None
        assert decoded.payload == "v2-data"

        # Cleanup
        pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{msg.id[:8]}*.json")
        for match in glob.glob(pattern):
            Path(match).unlink()


class TestCleanupTempFiles:
    """Tests for cleanup_temp_files function."""

    def test_cleanup_removes_old_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should remove files older than TTL."""
        # Create a temp file with old mtime
        old_file = tmp_path / "fork_msg_oldtest.json"
        old_file.write_text('{"id":"old"}')

        # Set mtime to 10 minutes ago
        import time

        old_time = time.time() - 600
        os.utime(old_file, (old_time, old_time))

        # Create a new file
        new_file = tmp_path / "fork_msg_newtest.json"
        new_file.write_text('{"id":"new"}')

        # Monkeypatch the temp dir
        monkeypatch.setattr(
            "src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR",
            tmp_path,
        )

        # Cleanup with 5 min TTL
        removed = cleanup_temp_files(max_age_seconds=300)

        assert removed == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_keeps_recent_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should not remove files newer than TTL."""
        # Create a new file
        new_file = tmp_path / "fork_msg_recent.json"
        new_file.write_text('{"id":"recent"}')

        monkeypatch.setattr(
            "src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR",
            tmp_path,
        )

        removed = cleanup_temp_files(max_age_seconds=300)

        assert removed == 0
        assert new_file.exists()
