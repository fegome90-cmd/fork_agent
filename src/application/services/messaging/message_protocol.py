"""Message protocol for inter-agent communication.

This module defines the encoding/decoding protocol for messages sent
between tmux sessions. Messages are encoded as JSON with a special prefix
for detection in capture-pane output.

Protocol v2 (Opción C): Ultra-short reference + temp file to minimize tokens.
"""

from __future__ import annotations

import glob
import json
import os
import time
from pathlib import Path
from typing import Any

from src.domain.entities.message import AgentMessage, MessageType

# Protocol v1: Full JSON inline (deprecated, kept for backward compatibility)
FORK_MSG_PREFIX = "# FORK_MSG:"

# Protocol v2: Ultra-short reference to temp file
FORK_MSG_SHORT_PREFIX = "# F:"
FORK_MSG_TEMP_DIR = Path(os.getenv("FORK_MSG_TEMP_DIR", "/tmp"))
FORK_MSG_TTL_SECONDS = int(os.getenv("FORK_MSG_TTL", "300"))  # 5 min default


def _get_temp_file_path(msg_id: str) -> Path:
    """Get temp file path for a message ID.

    Uses first 8 chars of ID for filename to keep terminal output short.
    """
    id_short = msg_id[:8] if len(msg_id) >= 8 else msg_id
    return FORK_MSG_TEMP_DIR / f"fork_msg_{id_short}.json"


def _write_temp_file(msg: AgentMessage, data: dict[str, Any]) -> None:
    """Write message data to temp file.

    Args:
        msg: The message being encoded
        data: The full JSON data to write
    """
    temp_path = _get_temp_file_path(msg.id)
    temp_path.write_text(json.dumps(data))


def _read_temp_file(msg_id_short: str) -> dict[str, Any] | None:
    """Read message data from temp file.

    Args:
        msg_id_short: First 8 chars of message ID

    Returns:
        Parsed JSON data or None if file not found/invalid
    """
    # Glob to find file (in case ID was truncated)
    pattern = str(FORK_MSG_TEMP_DIR / f"fork_msg_{msg_id_short}*.json")
    matches = glob.glob(pattern)

    if not matches:
        return None

    try:
        # Use first match
        data: dict[str, Any] = json.loads(Path(matches[0]).read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return None


def cleanup_temp_files(max_age_seconds: int | None = None) -> int:
    """Remove temp files older than TTL.

    Args:
        max_age_seconds: Override default TTL (for testing)

    Returns:
        Number of files removed
    """
    ttl = max_age_seconds or FORK_MSG_TTL_SECONDS
    cutoff = time.time() - ttl
    removed = 0

    for path in FORK_MSG_TEMP_DIR.glob("fork_msg_*.json"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed += 1

    return removed


def encode_message(msg: AgentMessage) -> str:
    """Encode message as ultra-short reference to temp file.

    Protocol v2: Write full JSON to temp file, return short reference.
    This minimizes tokens consumed by LLM when processing terminal output.

    Args:
        msg: The message to encode

    Returns:
        String in format "# F:{id_short}" (~15 chars, ~3 tokens)
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

    # Write full JSON to temp file
    _write_temp_file(msg, data)

    # Return ultra-short reference
    id_short = msg.id[:8] if len(msg.id) >= 8 else msg.id
    return f"{FORK_MSG_SHORT_PREFIX}{id_short}"


def decode_message(raw: str) -> AgentMessage | None:
    """Parse FORK_MSG from capture-pane output.

    Supports both protocols:
    - v2: "# F:{id_short}" -> reads from temp file
    - v1: "# FORK_MSG:{json}" -> parses inline (backward compatibility)

    Args:
        raw: Raw string that may contain a FORK_MSG

    Returns:
        AgentMessage if valid, None if invalid or malformed
    """
    # Try v2 protocol first (ultra-short reference)
    short_index = raw.find(FORK_MSG_SHORT_PREFIX)
    if short_index != -1:
        id_short = raw[short_index + len(FORK_MSG_SHORT_PREFIX) :].strip()[:8]
        data = _read_temp_file(id_short)
        if data:
            return _parse_message_data(data)

    # Fall back to v1 protocol (inline JSON)
    start_index = raw.find(FORK_MSG_PREFIX)
    if start_index == -1:
        return None

    try:
        json_part = raw[start_index + len(FORK_MSG_PREFIX) :].strip()
        data = json.loads(json_part)
    except (json.JSONDecodeError, TypeError):
        return None

    return _parse_message_data(data)


def _parse_message_data(data: dict[str, Any]) -> AgentMessage | None:
    """Parse AgentMessage from decoded JSON data.

    Args:
        data: Parsed JSON dictionary

    Returns:
        AgentMessage if valid, None if required fields missing
    """
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


def is_self_message(msg: AgentMessage, self_agent_id: str) -> bool:
    """Return True if the message was sent by this agent (loop guard).

    Use this before processing an incoming message to avoid infinite
    response loops where an agent reacts to its own output.

    Args:
        msg: The incoming AgentMessage to check
        self_agent_id: This agent's own session:window identifier

    Returns:
        True if msg.from_agent == self_agent_id
    """
    return msg.from_agent == self_agent_id


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
