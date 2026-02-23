"""AgentMessenger service for inter-agent communication.

This service coordinates message sending via tmux and persistent storage
via SQLite. It acts as the application layer interface for messaging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.services.messaging.message_protocol import encode_message
from src.domain.entities.message import AgentMessage, MessageType

if TYPE_CHECKING:
    from src.infrastructure.persistence.message_store import MessageStore
    from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class AgentMessenger:
    """Service for sending messages between tmux sessions.

    Coordinates:
    - Message encoding via protocol
    - Sending via tmux send-keys
    - Persistence via SQLite store
    """

    __slots__ = ("_orchestrator", "_store")

    def __init__(
        self,
        orchestrator: "TmuxOrchestrator",
        store: "MessageStore",
    ) -> None:
        """Initialize the messenger.

        Args:
            orchestrator: TmuxOrchestrator for tmux operations
            store: MessageStore for persistence
        """
        self._orchestrator = orchestrator
        self._store = store

    @property
    def orchestrator(self) -> "TmuxOrchestrator":
        """Get the orchestrator instance."""
        return self._orchestrator

    @property
    def store(self) -> "MessageStore":
        """Get the message store instance."""
        return self._store

    def send(self, msg: AgentMessage) -> bool:
        """Send a message via tmux and store it.

        The message is always stored for audit/retry purposes,
        even if tmux send fails.

        Args:
            msg: The message to send

        Returns:
            True if tmux send succeeded, False otherwise
        """
        # Always store the message first (for audit/retry)
        self._store.save(msg)

        # Parse session:window from to_agent
        parts = msg.to_agent.split(":")
        if len(parts) != 2:
            return False

        session, window_str = parts
        try:
            window = int(window_str)
        except ValueError:
            return False

        # Encode and send via tmux
        encoded = encode_message(msg)
        success = self._orchestrator.send_message(session, window, encoded)

        return success

    def broadcast(self, from_agent: str, payload: str) -> int:
        """Broadcast a message to all active sessions.

        Creates a COMMAND message with to_agent='*' and sends it to
        all active tmux sessions.

        Args:
            from_agent: Source session:window
            payload: Message payload (will be JSON-encoded if not already)

        Returns:
            Number of successful sends
        """
        sessions = self._orchestrator.get_sessions()
        success_count = 0

        for session in sessions:
            for window in session.windows:
                # Create broadcast message for this target
                msg = AgentMessage.create(
                    from_agent=from_agent,
                    to_agent=f"{session.name}:{window.window_index}",
                    message_type=MessageType.COMMAND,
                    payload=payload,
                )

                # Store and send
                self._store.save(msg)
                encoded = encode_message(msg)

                if self._orchestrator.send_message(
                    session.name, window.window_index, encoded
                ):
                    success_count += 1

        return success_count

    def get_messages(self, agent_id: str, limit: int = 50) -> list[AgentMessage]:
        """Get messages addressed to a specific agent.

        Args:
            agent_id: The agent's session:window identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages in descending order by created_at
        """
        return self._store.get_for_agent(agent_id, limit)

    def get_history(self, agent_id: str, limit: int = 100) -> list[AgentMessage]:
        """Get message history for an agent (sent and received).

        Args:
            agent_id: The agent's session:window identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages in descending order by created_at
        """
        return self._store.get_history(agent_id, limit)
