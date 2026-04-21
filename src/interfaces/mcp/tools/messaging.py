"""Inter-agent messaging tools: 4 MCP tools for send, receive, broadcast, history."""

from __future__ import annotations

import json
from typing import Any

from mcp import McpError
from mcp.types import INVALID_PARAMS, ErrorData

from src.interfaces.mcp.tools._shared import (
    _get_agent_messenger,
    _map_error,
    logger,
)


def _serialize_message(msg: Any) -> dict[str, Any]:
    """Serialize AgentMessage to MCP-safe dict."""
    return {
        "id": msg.id,
        "from": msg.from_agent,
        "to": msg.to_agent,
        "type": msg.message_type.name,
        "payload": msg.payload,
        "created_at": msg.created_at_iso,
    }


def _serialize_messages(msgs: list[Any]) -> list[dict[str, Any]]:
    """Serialize a list of AgentMessage entities."""
    return [_serialize_message(m) for m in msgs]


def fork_message_send(
    target: str,
    payload: str,
    from_agent: str | None = None,
    type: str | None = None,
) -> str:
    """Send a message to a target agent.

    Args:
        target: Target agent in session:window format (required).
        payload: Message content (required).
        from_agent: Source agent ID (default: 'cli:0').
        type: Message type: COMMAND, REPLY, HANDOFF, PROGRESS, FILE_TOUCHED, or OBSERVATION (default: 'COMMAND').

    Returns:
        JSON with status and target.
    """
    if not target.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="target must not be empty"))
    if not payload.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="payload must not be empty"))

    try:
        from src.domain.entities.message import AgentMessage, MessageType

        messenger = _get_agent_messenger()
        effective_from = from_agent or "cli:0"

        try:
            mtype = MessageType[(type or "COMMAND").upper()]
        except KeyError as e:
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Invalid message type: {type}")
            ) from e

        msg = AgentMessage.create(
            from_agent=effective_from, to_agent=target, message_type=mtype, payload=payload
        )
        success = messenger.send(msg)
        logger.info("fork_message_send: from=%s to=%s", effective_from, target)

        return json.dumps({"status": "sent" if success else "stored", "target": target})
    except McpError:
        raise
    except Exception as e:
        logger.error("fork_message_send failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def fork_message_receive(
    agent_id: str,
    limit: int | None = None,
    mark_read: bool | None = None,
) -> str:
    """Receive messages for an agent.

    Args:
        agent_id: Agent ID to receive messages for, in session:window format (required).
        limit: Maximum number of messages to retrieve (default: 10).
        mark_read: Whether to mark messages as read after retrieval (default: false).
            Read messages are automatically purged after 5 minutes.

    Returns:
        JSON array of messages.
    """
    if not agent_id.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="agent_id must not be empty"))

    try:
        messenger = _get_agent_messenger()
        messages = messenger.get_messages(agent_id, limit=limit or 10)
        logger.info("fork_message_receive: agent=%s count=%d", agent_id, len(messages))
        serialized = _serialize_messages(messages)

        if mark_read and messages:
            ids = [m.id for m in messages]
            messenger.mark_messages_read(ids)

        return json.dumps(serialized)
    except Exception as e:
        logger.error("fork_message_receive failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def fork_message_broadcast(
    payload: str,
    from_agent: str | None = None,
) -> str:
    """Broadcast a message to all active agent sessions.

    Args:
        payload: Message content to broadcast (required).
        from_agent: Source agent ID (default: 'cli:0').

    Returns:
        JSON with status and count of recipients.
    """
    if not payload.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="payload must not be empty"))

    try:
        messenger = _get_agent_messenger()
        effective_from = from_agent or "cli:0"
        count = messenger.broadcast(from_agent=effective_from, payload=payload)
        logger.info("fork_message_broadcast: from=%s recipients=%d", effective_from, count)

        return json.dumps({"status": "broadcast", "recipients": count})
    except Exception as e:
        logger.error("fork_message_broadcast failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def fork_message_history(
    agent_id: str,
    limit: int | None = None,
) -> str:
    """Get message history for an agent.

    Args:
        agent_id: Agent ID to show history for (required).
        limit: Maximum number of messages to return (default: 20).

    Returns:
        JSON array of historical messages (sent and received).
    """
    if not agent_id.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="agent_id must not be empty"))

    try:
        messenger = _get_agent_messenger()
        history = messenger.get_history(agent_id, limit=limit or 20)
        logger.info("fork_message_history: agent=%s count=%d", agent_id, len(history))
        serialized = _serialize_messages(history)

        return json.dumps(serialized)
    except Exception as e:
        logger.error("fork_message_history failed: %s", e, exc_info=True)
        raise _map_error(e) from e
