"""Message protocol for inter-agent communication.

This module defines the encoding/decoding protocol for messages sent
between tmux sessions. Messages are encoded as JSON with a special prefix
for detection in capture-pane output.
"""

from __future__ import annotations

import json
from typing import Any

from src.domain.entities.message import AgentMessage, MessageType

# Protocol prefix for detection in capture-pane output
# Prefixed with "# " so shells (fish/zsh/bash) treat it as a comment
FORK_MSG_PREFIX = "# FORK_MSG:"


def encode_message(msg: AgentMessage) -> str:
    """Encode message as FORK_MSG:<json> for tmux send-keys.

    Args:
        msg: The message to encode

    Returns:
        String in format "FORK_MSG:{...json...}"
    """
    data: dict[str, Any] = {
        "id": msg.id,
        "from_agent": msg.from_agent,
        "to_agent": msg.to_agent,
        "message_type": msg.message_type.name,
        "payload": msg.payload,
        "created_at": msg.created_at,
        "correlation_id": msg.correlation_id,
    }
    return f"{FORK_MSG_PREFIX}{json.dumps(data)}"


def decode_message(raw: str) -> AgentMessage | None:
    """Parse FORK_MSG:... from capture-pane output.

    Args:
        raw: Raw string that may contain a FORK_MSG

    Returns:
        AgentMessage if valid, None if invalid or malformed
    """
    # Find the start of FORK_MSG prefix in the raw string
    start_index = raw.find(FORK_MSG_PREFIX)
    if start_index == -1:
        return None

    try:
        json_part = raw[start_index + len(FORK_MSG_PREFIX) :].strip()
        data = json.loads(json_part)
    except (json.JSONDecodeError, TypeError):
        return None

    # Validate required fields
    required_fields = [
        "id",
        "from_agent",
        "to_agent",
        "message_type",
        "payload",
        "created_at",
    ]
    if not all(field in data for field in required_fields):
        return None

    try:
        message_type = MessageType[data["message_type"]]
    except KeyError:
        return None

    return AgentMessage(
        id=data["id"],
        from_agent=data["from_agent"],
        to_agent=data["to_agent"],
        message_type=message_type,
        payload=data["payload"],
        created_at=data["created_at"],
        correlation_id=data.get("correlation_id"),
    )


def create_command(from_: str, to: str, command: str, **kwargs: Any) -> AgentMessage:
    """Create a COMMAND message.

    Args:
        from_: Source session:window
        to: Target session:window (or "*" for broadcast)
        command: Command name
        **kwargs: Additional parameters to include in payload

    Returns:
        AgentMessage with COMMAND type
    """
    payload_data = {"command": command, **kwargs}
    return AgentMessage.create(
        from_agent=from_,
        to_agent=to,
        message_type=MessageType.COMMAND,
        payload=json.dumps(payload_data),
    )


def create_reply(from_: str, to: str, correlation_id: str, response: str) -> AgentMessage:
    """Create a REPLY message.

    Args:
        from_: Source session:window
        to: Target session:window
        correlation_id: ID of the original COMMAND message
        response: Response content

    Returns:
        AgentMessage with REPLY type
    """
    payload_data = {"response": response}
    return AgentMessage.create(
        from_agent=from_,
        to_agent=to,
        message_type=MessageType.REPLY,
        payload=json.dumps(payload_data),
        correlation_id=correlation_id,
    )


def create_handoff(from_: str, to: str, handoff_path: str) -> AgentMessage:
    """Create a HANDOFF message.

    Args:
        from_: Source session:window
        to: Target session:window
        handoff_path: Path to handoff context file

    Returns:
        AgentMessage with HANDOFF type
    """
    payload_data = {"handoff_path": handoff_path}
    return AgentMessage.create(
        from_agent=from_,
        to_agent=to,
        message_type=MessageType.HANDOFF,
        payload=json.dumps(payload_data),
    )
