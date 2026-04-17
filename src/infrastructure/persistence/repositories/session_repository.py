"""Session repository for SQLite persistence."""

from __future__ import annotations

import sqlite3

from src.application.exceptions import RepositoryError, SessionNotFoundError
from src.domain.entities.session import Session
from src.infrastructure.persistence.database import DatabaseConnection


class SessionRepositoryImpl:
    """Repository for persisting and retrieving Session entities.

    Provides CRUD operations for session lifecycle management.
    """

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def create(self, session: Session) -> None:
        """Store a new session in the database.

        Args:
            session: The session entity to persist.

        Raises:
            RepositoryError: If the session ID already exists or database error occurs.
        """
        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT INTO sessions
                        (id, project, directory, started_at, ended_at, goal, instructions, summary)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        session.id,
                        session.project,
                        session.directory,
                        session.started_at,
                        session.ended_at,
                        session.goal,
                        session.instructions,
                        session.summary,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"Session with id '{session.id}' already exists",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to create session: {e}", e) from e

    def get_by_id(self, session_id: str) -> Session:
        """Retrieve a session by its ID.

        Args:
            session_id: The unique identifier of the session.

        Returns:
            The session entity if found.

        Raises:
            SessionNotFoundError: If no session exists with the given ID.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, project, directory, started_at, ended_at,
                        goal, instructions, summary
                        FROM sessions WHERE id = ?""",
                    (session_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise SessionNotFoundError(f"Session '{session_id}' not found")
                return self._row_to_session(row)
        except SessionNotFoundError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get session: {e}", e) from e

    def get_recent(self, project: str, limit: int = 10) -> list[Session]:
        """Get recent sessions for a project.

        Args:
            project: The project name to filter by.
            limit: Maximum number of sessions to return.

        Returns:
            List of session entities ordered by started_at descending.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, project, directory, started_at, ended_at,
                        goal, instructions, summary
                        FROM sessions
                        WHERE project = ?
                        ORDER BY started_at DESC
                        LIMIT ?""",
                    (project, limit),
                )
                rows = cursor.fetchall()
                return [self._row_to_session(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get recent sessions: {e}", e) from e

    def end_session(self, session_id: str, summary: str | None = None) -> Session:
        """End an active session.

        Args:
            session_id: The ID of the session to end.
            summary: Optional summary of what was accomplished.

        Returns:
            The updated session entity.

        Raises:
            SessionNotFoundError: If no session exists with the given ID.
        """
        import time

        try:
            ended_at = int(time.time() * 1000)

            with self._connection as conn:
                # First check if session exists
                cursor = conn.execute(
                    """SELECT id, project, directory, started_at, ended_at,
                        goal, instructions, summary
                        FROM sessions WHERE id = ?""",
                    (session_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise SessionNotFoundError(f"Session '{session_id}' not found")

                session = self._row_to_session(row)

                # Update the session
                conn.execute(
                    """UPDATE sessions
                        SET ended_at = ?, summary = ?
                        WHERE id = ?""",
                    (ended_at, summary, session_id),
                )

                # Return updated session
                return Session(
                    id=session.id,
                    project=session.project,
                    directory=session.directory,
                    started_at=session.started_at,
                    ended_at=ended_at,
                    goal=session.goal,
                    instructions=session.instructions,
                    summary=summary,
                )
        except SessionNotFoundError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to end session: {e}", e) from e

    def get_active(self, project: str) -> Session | None:
        """Get the active session for a project.

        Args:
            project: The project name to check.

        Returns:
            The active session if one exists, None otherwise.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, project, directory, started_at, ended_at,
                        goal, instructions, summary
                        FROM sessions
                        WHERE project = ? AND ended_at IS NULL
                        ORDER BY started_at DESC
                        LIMIT 1""",
                    (project,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_session(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get active session: {e}", e) from e

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert a database row to a Session entity."""
        return Session(
            id=row["id"],
            project=row["project"],
            directory=row["directory"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            goal=row["goal"],
            instructions=row["instructions"],
            summary=row["summary"],
        )
