"""Messaging services for inter-agent communication."""

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.application.services.messaging.message_protocol import (
    FORK_MSG_PREFIX,
    FORK_MSG_SHORT_PREFIX,
    FORK_MSG_TEMP_DIR,
    FORK_MSG_TTL_SECONDS,
    cleanup_temp_files,
    create_command,
    create_handoff,
    create_reply,
    decode_message,
    encode_message,
    is_self_message,
)

__all__ = [
    "AgentMessenger",
    "FORK_MSG_PREFIX",
    "FORK_MSG_SHORT_PREFIX",
    "FORK_MSG_TEMP_DIR",
    "FORK_MSG_TTL_SECONDS",
    "cleanup_temp_files",
    "create_command",
    "create_handoff",
    "create_reply",
    "decode_message",
    "encode_message",
    "is_self_message",
]
