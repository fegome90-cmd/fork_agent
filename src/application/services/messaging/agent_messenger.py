"""AgentMessenger service for inter-agent communication.

This service coordinates message sending via tmux and persistent storage
via SQLite. It acts as the application layer interface for messaging.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.application.services.messaging.message_protocol import cleanup_temp_files, encode_message
from src.domain.entities.message import AgentMessage, MessageType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.infrastructure.persistence.message_store import MessageStore
    from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

# Allowed prefixes for session names to avoid sending messages to non-agent sessions
ALLOWED_SESSION_PREFIXES = ("fork-", "agent-", "opencode-")


class AgentMessenger:
    """Service for sending messages between tmux sessions.

    Coordinates:
    - Message encoding via protocol
    - Sending via tmux notifications (silent)
    - Persistence via SQLite store (authoritative)
    """

    def __init__(
        self,
        orchestrator: TmuxOrchestrator,
        store: MessageStore,
    ) -> None:
        """Initialize the messenger.

        Args:
            orchestrator: TmuxOrchestrator for tmux operations
            store: MessageStore for persistence
        """
        self._orchestrator = orchestrator
        self._store = store
        self._last_maintenance = 0.0

    @property
    def orchestrator(self) -> TmuxOrchestrator:
        return self._orchestrator

    @property
    def store(self) -> MessageStore:
        return self._store

    def send(self, msg: AgentMessage) -> bool:
        """Send a message via shared DB and silent notification."""
        # 0. Validation (Fail fast)
        parts = msg.to_agent.split(":")
        if len(parts) != 2:
            logging.error(f"Invalid target agent format: {msg.to_agent}. Expected 'session:window'")
            return False

        target_session, window_index = parts

        # 1. Authoritative Store (DB is the transport)
        # Note: self._store.save() now triggers auto-cleanup of expired and hard-limit pruning
        self._store.save(msg)

        # 2. Ephemeral Maintenance (Filesystem protection)
        import time

        now = time.time()
        if now - self._last_maintenance > 30:  # Every 30 seconds max
            cleanup_temp_files(max_age_seconds=60)
            self._last_maintenance = now

        # 3. Persist to temp storage for v2 protocol decoding
        try:
            encoded_msg = encode_message(msg)
        except Exception as e:
            logging.error(f"Failed to encode message for protocol v2: {e}")
            return False

        # 4. Background Signaling (Side-channel)
        # We use Tmux User Options as an invisible side-channel for agents.
        # This is 100% clean and doesn't affect the human UI (status bar).
        import subprocess

        try:
            # Check if session exists first
            check = subprocess.run(
                ["tmux", "has-session", "-t", target_session], capture_output=True
            )
            if check.returncode != 0:
                logging.debug(f"Messaging target session not found: {target_session}")
                return False

            # Set the message ID as a pane option (Side-channel)
            subprocess.run(
                [
                    "tmux",
                    "set-option",
                    "-p",
                    "-t",
                    f"{target_session}:{window_index}",
                    "@last_fork_msg",
                    encoded_msg,
                ],
                capture_output=True,
            )

            # 5. UI Notification (Optional/Discreet)
            # To avoid "hiding sessions", we ONLY send display-message if the target
            # is NOT our current session. Even then, we use a very short message.
            current_session = self._get_current_session()
            if target_session != current_session:
                # We show a generic notification that doesn't leak IDs to the status bar
                # but alerts the user/agent that something happened.
                subprocess.run(
                    [
                        "tmux",
                        "display-message",
                        "-t",
                        target_session,
                        f"FORK: Msg from {msg.from_agent}",
                    ],
                    capture_output=True,
                    timeout=1,
                )

            return True
        except Exception as e:
            logging.error(f"Failed to send tmux notification: {e}")
            return False

    def _get_current_session(self) -> str | None:
        """Identify current tmux session name safely."""
        import os
        import subprocess

        if "TMUX" not in os.environ:
            return None
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#S"], capture_output=True, text=True, timeout=1
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            logger.debug("Failed to detect tmux session", exc_info=True)
            return None

    def broadcast(self, from_agent: str, payload: str) -> int:
        """Broadcast a message to all active agent sessions.

        Excludes the current session to avoid UI noise (hiding status bar).
        """
        sessions = self._orchestrator.get_sessions()
        current_session = self._get_current_session()
        success_count = 0

        for session in sessions:
            # Skip current session (the orchestrator) to avoid UI flickering/hiding
            if session.name == current_session:
                continue

            # Only broadcast to sessions that look like agents
            if not any(session.name.startswith(p) for p in ALLOWED_SESSION_PREFIXES):
                continue

            for window in session.windows:
                # Create broadcast message for this target
                msg = AgentMessage.create(
                    from_agent=from_agent,
                    to_agent=f"{session.name}:{window.window_index}",
                    message_type=MessageType.COMMAND,
                    payload=payload,
                )

                # Use the silent send method
                if self.send(msg):
                    success_count += 1

        return success_count

    def get_messages(self, agent_id: str, limit: int = 50) -> list[AgentMessage]:
        """Get messages addressed to a specific agent."""
        return self._store.get_for_agent(agent_id, limit)

    def get_history(self, agent_id: str, limit: int = 100) -> list[AgentMessage]:
        """Get message history for an agent (sent and received)."""
        return self._store.get_history(agent_id, limit)

    def delete_messages(self, message_ids: list[str]) -> int:
        """Delete messages by their IDs."""
        return self._store.delete_by_ids(message_ids)
