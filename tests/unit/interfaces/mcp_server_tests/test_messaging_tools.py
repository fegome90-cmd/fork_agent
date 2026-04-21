"""Unit tests for MCP inter-agent messaging tool handlers."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from mcp import McpError
from mcp.types import INVALID_PARAMS

from src.domain.entities.message import AgentMessage, MessageType


def _make_message(
    id: str = "msg-uuid-1234",
    from_agent: str = "agent-1:0",
    to_agent: str = "agent-2:0",
    message_type: MessageType = MessageType.COMMAND,
    payload: str = '{"task": "explore"}',
    created_at: int | None = None,
) -> AgentMessage:
    return AgentMessage(
        id=id,
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        payload=payload,
        created_at=created_at or int(time.time() * 1000),
    )


# ---------------------------------------------------------------------------
# fork_message_send
# ---------------------------------------------------------------------------


class TestForkMessageSend:
    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_returns_sent_status_and_target(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        mock_get.return_value.send.return_value = True
        result = json.loads(fork_message_send(target="agent-2:0", payload="do work"))

        assert result["status"] == "sent"
        assert result["target"] == "agent-2:0"

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_stored_when_send_returns_false(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        mock_get.return_value.send.return_value = False
        result = json.loads(fork_message_send(target="agent-2:0", payload="do work"))

        assert result["status"] == "stored"

    def test_empty_target_raises(self) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        with pytest.raises(McpError) as exc_info:
            fork_message_send(target="  ", payload="data")

        assert exc_info.value.error.code == INVALID_PARAMS

    def test_empty_payload_raises(self) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        with pytest.raises(McpError) as exc_info:
            fork_message_send(target="agent-2:0", payload="  ")

        assert exc_info.value.error.code == INVALID_PARAMS

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_default_from_agent_is_cli0(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        mock_get.return_value.send.return_value = True
        fork_message_send(target="agent-2:0", payload="data")

        sent_msg = mock_get.return_value.send.call_args[0][0]
        assert sent_msg.from_agent == "cli:0"

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_default_type_is_command(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        mock_get.return_value.send.return_value = True
        fork_message_send(target="agent-2:0", payload="data")

        sent_msg = mock_get.return_value.send.call_args[0][0]
        assert sent_msg.message_type == MessageType.COMMAND

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_custom_from_agent_and_type(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        mock_get.return_value.send.return_value = True
        fork_message_send(
            target="agent-2:0",
            payload="data",
            from_agent="orchestrator:0",
            type="PROGRESS",
        )

        sent_msg = mock_get.return_value.send.call_args[0][0]
        assert sent_msg.from_agent == "orchestrator:0"
        assert sent_msg.message_type == MessageType.PROGRESS

    def test_invalid_type_raises(self) -> None:
        from src.interfaces.mcp.tools import fork_message_send

        with pytest.raises(McpError) as exc_info:
            fork_message_send(target="agent-2:0", payload="data", type="BOGUS")

        assert exc_info.value.error.code == INVALID_PARAMS
        assert "Invalid message type" in exc_info.value.error.message


# ---------------------------------------------------------------------------
# fork_message_receive
# ---------------------------------------------------------------------------


class TestForkMessageReceive:
    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_returns_json_array_of_messages(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        msgs = [_make_message(id="m1"), _make_message(id="m2")]
        mock_get.return_value.get_messages.return_value = msgs

        result = json.loads(fork_message_receive(agent_id="agent-1:0"))

        assert len(result) == 2
        assert result[0]["id"] == "m1"
        assert result[1]["id"] == "m2"

    def test_empty_agent_id_raises(self) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        with pytest.raises(McpError) as exc_info:
            fork_message_receive(agent_id="  ")

        assert exc_info.value.error.code == INVALID_PARAMS

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_limit_passed_to_messenger(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        mock_get.return_value.get_messages.return_value = []
        fork_message_receive(agent_id="agent-1:0", limit=5)

        mock_get.return_value.get_messages.assert_called_once_with("agent-1:0", limit=5)

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_default_limit_is_10(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        mock_get.return_value.get_messages.return_value = []
        fork_message_receive(agent_id="agent-1:0")

        mock_get.return_value.get_messages.assert_called_once_with("agent-1:0", limit=10)

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_mark_read_calls_delete(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        msgs = [_make_message(id="m1"), _make_message(id="m2")]
        mock_get.return_value.get_messages.return_value = msgs

        fork_message_receive(agent_id="agent-1:0", mark_read=True)

        mock_get.return_value.mark_messages_read.assert_called_once_with(["m1", "m2"])

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_mark_read_false_does_not_delete(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        msgs = [_make_message(id="m1")]
        mock_get.return_value.get_messages.return_value = msgs

        fork_message_receive(agent_id="agent-1:0", mark_read=False)

        mock_get.return_value.delete_messages.assert_not_called()

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_mark_read_default_does_not_delete(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        msgs = [_make_message(id="m1")]
        mock_get.return_value.get_messages.return_value = msgs

        fork_message_receive(agent_id="agent-1:0")

        mock_get.return_value.delete_messages.assert_not_called()

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_empty_result_returns_empty_array(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        mock_get.return_value.get_messages.return_value = []
        result = fork_message_receive(agent_id="agent-1:0")

        assert json.loads(result) == []

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_mark_read_no_messages_does_not_delete(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_receive

        mock_get.return_value.get_messages.return_value = []
        fork_message_receive(agent_id="agent-1:0", mark_read=True)

        mock_get.return_value.delete_messages.assert_not_called()


# ---------------------------------------------------------------------------
# fork_message_broadcast
# ---------------------------------------------------------------------------


class TestForkMessageBroadcast:
    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_returns_broadcast_status_and_count(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_broadcast

        mock_get.return_value.broadcast.return_value = 3
        result = json.loads(fork_message_broadcast(payload="hello everyone"))

        assert result["status"] == "broadcast"
        assert result["recipients"] == 3

    def test_empty_payload_raises(self) -> None:
        from src.interfaces.mcp.tools import fork_message_broadcast

        with pytest.raises(McpError) as exc_info:
            fork_message_broadcast(payload="  ")

        assert exc_info.value.error.code == INVALID_PARAMS

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_default_from_agent_is_cli0(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_broadcast

        mock_get.return_value.broadcast.return_value = 0
        fork_message_broadcast(payload="data")

        mock_get.return_value.broadcast.assert_called_once_with(from_agent="cli:0", payload="data")

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_custom_from_agent_passed(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_broadcast

        mock_get.return_value.broadcast.return_value = 2
        fork_message_broadcast(payload="data", from_agent="orchestrator:0")

        mock_get.return_value.broadcast.assert_called_once_with(
            from_agent="orchestrator:0", payload="data"
        )


# ---------------------------------------------------------------------------
# fork_message_history
# ---------------------------------------------------------------------------


class TestForkMessageHistory:
    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_returns_json_array(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_history

        msgs = [_make_message(id="h1"), _make_message(id="h2")]
        mock_get.return_value.get_history.return_value = msgs

        result = json.loads(fork_message_history(agent_id="agent-1:0"))

        assert len(result) == 2
        assert result[0]["id"] == "h1"
        assert result[1]["id"] == "h2"

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_agent_id_passed_correctly(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_history

        mock_get.return_value.get_history.return_value = []
        fork_message_history(agent_id="orchestrator:0")

        mock_get.return_value.get_history.assert_called_once_with("orchestrator:0", limit=20)

    def test_empty_agent_id_raises(self) -> None:
        from src.interfaces.mcp.tools import fork_message_history

        with pytest.raises(McpError) as exc_info:
            fork_message_history(agent_id="  ")

        assert exc_info.value.error.code == INVALID_PARAMS

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_limit_passed_to_messenger(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_history

        mock_get.return_value.get_history.return_value = []
        fork_message_history(agent_id="agent-1:0", limit=5)

        mock_get.return_value.get_history.assert_called_once_with("agent-1:0", limit=5)

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_default_limit_is_20(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_history

        mock_get.return_value.get_history.return_value = []
        fork_message_history(agent_id="agent-1:0")

        mock_get.return_value.get_history.assert_called_once_with("agent-1:0", limit=20)

    @patch("src.interfaces.mcp.tools.messaging._get_agent_messenger")
    def test_empty_history_returns_empty_array(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import fork_message_history

        mock_get.return_value.get_history.return_value = []
        result = fork_message_history(agent_id="agent-1:0")

        assert json.loads(result) == []
