"""SQLite-based message store for inter-agent communication.

This module provides persistent storage for messages using SQLite.
It acts as the single source of truth for message history.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.tmux_orchestrator import ORCHESTRATOR_DIR

# Default TTL for messages: 24 hours in milliseconds
DEFAULT_MESSAGE_TTL_MS = 24 * 60 * 60 * 1000


class MessageStore:
    """SQLite-based persistent message store.

    Provides CRUD operations for messages with automatic expiration.
    """

    __slots__ = ("_db_path", "_conn")

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the message store.

        Args:
            db_path: Path to SQLite database file. Defaults to
                     .tmux-orchestrator/messages.db
        """
        self._db_path = db_path or (ORCHESTRATOR_DIR / "messages.db")
        self._ensure_db()
        self._conn: sqlite3.Connection | None = None

    def _ensure_db(self) -> None:
        """Ensure database directory and tables exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self._db_path)) as conn:
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

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def save(self, msg: AgentMessage) -> None:
        """Save a message to the store.

        Args:
            msg: The message to save
        """
        expires_at = msg.created_at + DEFAULT_MESSAGE_TTL_MS

        conn = self._get_connection()
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
        """Get messages addressed to a specific agent.

        Includes both direct messages (to_agent == agent_id) and broadcast
        messages (to_agent == '*').

        Args:
            agent_id: The agent's session:window identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages in descending order by created_at (newest first)
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM messages
            WHERE to_agent = ? OR to_agent = '*'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (agent_id, limit),
        )

        return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_history(self, agent_id: str, limit: int = 100) -> list[AgentMessage]:
        """Get message history involving an agent (sent or received).

        Args:
            agent_id: The agent's session:window identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages in descending order by created_at (newest first)
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM messages
            WHERE from_agent = ? OR to_agent = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (agent_id, agent_id, limit),
        )

        return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_by_correlation(self, correlation_id: str) -> list[AgentMessage]:
        """Get messages by correlation ID for request/response matching.

        Args:
            correlation_id: The correlation ID to search for

        Returns:
            List of messages with the given correlation_id
        """
        conn = self._get_connection()
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
        """Remove messages that have expired.

        Returns:
            Number of messages removed
        """
        import time

        now_ms = int(time.time() * 1000)
        conn = self._get_connection()

        cursor = conn.execute(
            "DELETE FROM messages WHERE expires_at < ?",
            (now_ms,),
        )
        conn.commit()

        return cursor.rowcount

    def get_db_path(self) -> Path:
        """Get the database file path.

        Returns:
            Path to the SQLite database file
        """
        return self._db_path

    def _row_to_message(self, row: sqlite3.Row) -> AgentMessage:
        """Convert a database row to an AgentMessage.

        Args:
            row: SQLite row with message data

        Returns:
            AgentMessage instance
        """
        return AgentMessage(
            id=row["id"],
            from_agent=row["from_agent"],
            to_agent=row["to_agent"],
            message_type=MessageType[row["message_type"]],
            payload=row["payload"],
            created_at=row["created_at"],
            correlation_id=row["correlation_id"],
        )
