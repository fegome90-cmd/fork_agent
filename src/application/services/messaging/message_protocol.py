"""Message protocol for inter-agent communication.

This module defines the encoding/decoding protocol for messages sent
between tmux sessions. Messages are encoded as JSON with a special prefix
for detection in capture-pane output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.domain.entities.message import AgentMessage, MessageType

# Protocol prefix for detection in capture-pane output
# Prefixed with "# " so shells (fish/zsh/bash) treat it as a comment
FORK_MSG_PREFIX = "# FORK_MSG:"
FORK_MSG_SHORT_PREFIX = "# F:"
FORK_MSG_TEMP_DIR = Path("/tmp/fork-messages")


def encode_message(msg: AgentMessage) -> str:
    """Encode message using v2 short protocol for tmux send-keys.

    Writes full JSON to temp file, returns short reference.
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

    # v2: write full JSON to temp file, return short reference
    try:
        FORK_MSG_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = FORK_MSG_TEMP_DIR / f"fork_msg_{msg.id[:8]}.json"
        temp_file.write_text(json.dumps(data))
    except (OSError, IOError) as e:
        # Re-raise to let the messenger know the protocol failed
        raise RuntimeError(f"Failed to write message to temp storage: {e}")

    return f"# F:{msg.id[:8]}"


def decode_message(raw: str) -> AgentMessage | None:
    """Parse message from string, enforcing strict prefix rules."""
    # 1. Try v2 short prefix (# F:) - MUST be present
    start_index = raw.find("# F:")
    if start_index != -1:
        # Extract 8-char ID (securely)
        suffix = raw[start_index + 4:].strip()
        if not suffix:
            return None
            
        id_part = suffix.split()[0] # Take until whitespace
        id_short = id_part[:8]
        
        temp_file = FORK_MSG_TEMP_DIR / f"fork_msg_{id_short}.json"
        if temp_file.exists():
            try:
                data = json.loads(temp_file.read_text())
                return _create_from_dict(data)
            except (json.JSONDecodeError, OSError):
                return None
        return None

    # 2. Try v1 full prefix (# FORK_MSG:) - Fallback for small messages
    start_index = raw.find(FORK_MSG_PREFIX)
    if start_index != -1:
        try:
            json_part = raw[start_index + len(FORK_MSG_PREFIX) :].strip()
            data = json.loads(json_part)
            return _create_from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return None

    return None


def _create_from_dict(data: dict[str, Any]) -> AgentMessage | None:
    """Helper to create AgentMessage from dictionary with validation."""
    required = ["id", "from_agent", "to_agent", "message_type", "payload", "created_at"]
    if not all(field in data for field in required):
        return None

    try:
        return AgentMessage(
            id=data["id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            message_type=MessageType[data["message_type"]],
            payload=data["payload"],
            created_at=data["created_at"],
            correlation_id=data.get("correlation_id"),
        )
    except (KeyError, ValueError):
        return None


def create_command(from_: str, to: str, command: str, **kwargs: Any) -> AgentMessage:
    """Create a COMMAND message."""
    payload_data = {"command": command, **kwargs}
    return AgentMessage.create(
        from_agent=from_,
        to_agent=to,
        message_type=MessageType.COMMAND,
        payload=json.dumps(payload_data),
    )


def create_reply(from_: str, to: str, correlation_id: str, response: str) -> AgentMessage:
    """Create a REPLY message."""
    payload_data = {"response": response}
    return AgentMessage.create(
        from_agent=from_,
        to_agent=to,
        message_type=MessageType.REPLY,
        payload=json.dumps(payload_data),
        correlation_id=correlation_id,
    )


def create_handoff(from_: str, to: str, handoff_path: str) -> AgentMessage:
    """Create a HANDOFF message."""
    payload_data = {"handoff_path": handoff_path}
    return AgentMessage.create(
        from_agent=from_,
        to_agent=to,
        message_type=MessageType.HANDOFF,
        payload=json.dumps(payload_data),
    )


def cleanup_temp_files(max_age_seconds: int = 60) -> int:
    """Remove temp message files older than max_age_seconds.

    Default is 60 seconds as these files are ephemeral handoffs.
    """
    import time
    removed = 0
    if not FORK_MSG_TEMP_DIR.exists():
        return removed
    now = time.time()
    for f in FORK_MSG_TEMP_DIR.glob("fork_msg_*.json"):
        try:
            if f.is_file() and (now - f.stat().st_mtime) > max_age_seconds:
                f.unlink()
                removed += 1
        except (OSError, FileNotFoundError):
            # File might have been deleted by another process
            pass
    return removed
