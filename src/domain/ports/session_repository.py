"""Ports (Protocols) for Session persistence operations."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.session import Session


class SessionRepository(Protocol):
    """Protocol for session persistence."""

    def create(self, session: Session) -> None:
        """Create a new session.

        Args:
            session: The session entity to persist.
        """
        ...

    def get_by_id(self, session_id: str) -> Session:
        """Retrieve a session by its ID.

        Args:
            session_id: The unique identifier of the session.

        Returns:
            The session entity if found.

        Raises:
            SessionNotFoundError: If no session exists with the given ID.
        """
        ...

    def get_recent(self, project: str, limit: int = 10) -> list[Session]:
        """Get recent sessions for a project.

        Args:
            project: The project name to filter by.
            limit: Maximum number of sessions to return.

        Returns:
            List of session entities ordered by started_at descending.
        """
        ...

    def end_session(self, session_id: str, summary: str | None) -> Session:
        """End an active session.

        Args:
            session_id: The ID of the session to end.
            summary: Optional summary of what was accomplished.

        Returns:
            The updated session entity.

        Raises:
            SessionNotFoundError: If no session exists with the given ID.
        """
        ...

    def get_active(self, project: str) -> Session | None:
        """Get the active session for a project.

        Args:
            project: The project name to check.

        Returns:
            The active session if one exists, None otherwise.
        """
        ...

    def update(self, session: Session) -> None:
        """Update an existing session.

        Args:
            session: The session entity with updated values.

        Raises:
            SessionNotFoundError: If no session exists with the given ID.
        """
        ...
