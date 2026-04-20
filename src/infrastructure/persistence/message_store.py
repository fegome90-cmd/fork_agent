"""SQLite-based message store for inter-agent communication."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from src.domain.entities.message import AgentMessage, MessageType

if TYPE_CHECKING:
    from src.infrastructure.persistence.database import DatabaseConnection

# Default TTL for messages: 24 hours in milliseconds
DEFAULT_MESSAGE_TTL_MS = 24 * 60 * 60 * 1000
# Hard limit for total messages in DB to prevent disk exhaustion
MAX_TOTAL_MESSAGES = 5000


class MessageStore:
    """SQLite-based persistent message store using shared connection."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        """Initialize the message store.

        Args:
            connection: Shared DatabaseConnection instance.
        """
        self._connection = connection
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database tables exist using authoritative connection."""
        with self._connection as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    correlation_id TEXT,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_messages_to_agent
                    ON messages(to_agent, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_from_agent
                    ON messages(from_agent, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_correlation
                    ON messages(correlation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_expires_at
                    ON messages(expires_at);
                """
            )
            conn.commit()

    def save(self, msg: AgentMessage) -> None:
        """Save a message to the store and maintain hygiene."""
        # 1. Self-healing: Purge expired before adding new ones
        self.cleanup_expired()

        expires_at = msg.created_at + DEFAULT_MESSAGE_TTL_MS

        with self._connection as conn:
            # 2. Hard cap enforcement: Delete oldest if we exceed MAX_TOTAL_MESSAGES
            # (Simple but effective protection against infinite loops/GBs of disk)
            conn.execute(
                """
                DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages
                    ORDER BY created_at ASC
                    LIMIT MAX(0, (SELECT COUNT(*) FROM messages) - ?)
                )
                """,
                (MAX_TOTAL_MESSAGES - 1,),
            )

            conn.execute(
                """
                INSERT INTO messages (
                    id, from_agent, to_agent, message_type, payload,
                    correlation_id, created_at, expires_at, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    msg.id,
                    msg.from_agent,
                    msg.to_agent,
                    msg.message_type.name,
                    msg.payload,
                    msg.correlation_id,
                    msg.created_at,
                    expires_at,
                ),
            )
            conn.commit()

    def get_for_agent(self, agent_id: str, limit: int = 50) -> list[AgentMessage]:
        """Get messages addressed to a specific agent."""
        with self._connection as conn:
            cursor = conn.execute(
                """
                SELECT * FROM messages
                WHERE to_agent = ? OR to_agent = '*'
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (agent_id, limit),
            )
            return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_history(self, agent_id: str, limit: int = 100) -> list[AgentMessage]:
        """Get message history involving an agent."""
        with self._connection as conn:
            cursor = conn.execute(
                """
                SELECT * FROM messages
                WHERE from_agent = ? OR to_agent = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (agent_id, agent_id, limit),
            )
            return [self._row_to_message(row) for row in cursor.fetchall()]

    def _row_to_message(self, row: sqlite3.Row) -> AgentMessage:
        """Convert a database row to an AgentMessage."""
        return AgentMessage(
            id=row["id"],
            from_agent=row["from_agent"],
            to_agent=row["to_agent"],
            message_type=MessageType[row["message_type"]],
            payload=row["payload"],
            created_at=row["created_at"],
            correlation_id=row["correlation_id"],
        )

    def get_by_correlation(self, correlation_id: str) -> list[AgentMessage]:
        """Get messages by correlation ID for request/response matching."""
        with self._connection as conn:
            cursor = conn.execute(
                """
                SELECT * FROM messages
                WHERE correlation_id = ?
                ORDER BY created_at ASC
                """,
                (correlation_id,),
            )
            return [self._row_to_message(row) for row in cursor.fetchall()]

    def cleanup_expired(self) -> int:
        """Remove messages that have expired."""
        import time

        now_ms = int(time.time() * 1000)
        with self._connection as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE expires_at < ?",
                (now_ms,),
            )
            conn.commit()
            return cursor.rowcount
