"""Domain entity for agent messages.

This module defines the core message structure for inter-agent communication
via tmux sessions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC
from enum import Enum, auto


class MessageType(Enum):
    """Types of messages between agents.

    Simplified to 3 types:
    - COMMAND: Task assignment or request
    - REPLY: Response to a command
    - HANDOFF: Session handoff notification

    Broadcast is determined by to_agent='*' rather than a separate type.
    """

    COMMAND = auto()
    REPLY = auto()
    HANDOFF = auto()


@dataclass(frozen=True)
class AgentMessage:
    """Immutable message between agents.

    Represents a structured message sent between tmux sessions.
    Uses JSON payload for flexibility and millisecond timestamps for precision.

    Attributes:
        id: Unique identifier (UUID)
        from_agent: Source session:window (e.g., "agent1:0")
        to_agent: Target session:window or "*" for broadcast
        message_type: Type of message (COMMAND, REPLY, HANDOFF)
        payload: JSON-encoded message content
        created_at: Unix timestamp in milliseconds
        correlation_id: Optional ID for request/response matching
    """

    id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: str
    created_at: int
    correlation_id: str | None = None

    @property
    def created_at_iso(self) -> str:
        """Get the creation time as an ISO-formatted string."""
        from datetime import datetime

        return datetime.fromtimestamp(self.created_at / 1000, tz=UTC).isoformat()

    @classmethod
    def create(
        cls,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        payload: str,
        correlation_id: str | None = None,
    ) -> AgentMessage:
        """Factory method to create a new message with auto-generated ID and timestamp.

        Args:
            from_agent: Source session:window identifier
            to_agent: Target session:window or "*" for broadcast
            message_type: Type of message
            payload: JSON-encoded content
            correlation_id: Optional correlation ID for request/response matching

        Returns:
            A new AgentMessage instance with generated ID and current timestamp
        """
        return cls(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            created_at=int(time.time() * 1000),
            correlation_id=correlation_id,
        )
