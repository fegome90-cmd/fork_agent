"""Session service for session lifecycle management."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from src.application.exceptions import ServiceError, SessionNotFoundError
from src.domain.entities.session import Session
from src.infrastructure.persistence.repositories.session_repository import (
    SessionRepositoryImpl,
)


class SessionService:
    """Service for managing sessions with business logic."""

    __slots__ = ("_repository",)

    def __init__(self, repository: SessionRepositoryImpl) -> None:
        self._repository = repository

    def start_session(
        self,
        project: str,
        directory: str,
        goal: str | None = None,
        instructions: str | None = None,
    ) -> Session:
        """Start a new session.

        Args:
            project: Project name for the session.
            directory: Working directory path.
            goal: Optional goal description.
            instructions: Optional instructions/constraints.

        Returns:
            The newly created Session entity.

        Raises:
            ServiceError: If session creation fails.
        """
        try:
            # Check if there's already an active session for this project
            active = self._repository.get_active(project)
            if active is not None:
                # Auto-end the previous active session
                self._repository.end_session(
                    active.id,
                    summary="Auto-ended: new session started",
                )

            session_id = str(uuid.uuid4())
            started_at = int(time.time() * 1000)

            session = Session(
                id=session_id,
                project=project,
                directory=directory,
                started_at=started_at,
                ended_at=None,
                goal=goal,
                instructions=instructions,
                summary=None,
            )

            self._repository.create(session)
            return session
        except Exception as e:
            raise ServiceError(f"Failed to start session: {e}", e) from e

    def end_session(self, session_id: str, summary: str | None = None) -> Session:
        """End an active session.

        Args:
            session_id: The ID of the session to end.
            summary: Optional summary of what was accomplished.

        Returns:
            The updated Session entity.

        Raises:
            SessionNotFoundError: If the session does not exist.
            ServiceError: If ending the session fails.
        """
        try:
            return self._repository.end_session(session_id, summary)
        except SessionNotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to end session: {e}", e) from e

    def get_context(self, project: str, limit: int = 3) -> list[Session]:
        """Get recent sessions for context recovery.

        Args:
            project: The project name to filter by.
            limit: Maximum number of sessions to return.

        Returns:
            List of recent Session entities.

        Raises:
            ServiceError: If fetching sessions fails.
        """
        try:
            return self._repository.get_recent(project, limit=limit)
        except Exception as e:
            raise ServiceError(f"Failed to get session context: {e}", e) from e

    def get_active(self, project: str) -> Session | None:
        """Get the active session for a project.

        Args:
            project: The project name to check.

        Returns:
            The active Session if one exists, None otherwise.

        Raises:
            ServiceError: If fetching the session fails.
        """
        try:
            return self._repository.get_active(project)
        except Exception as e:
            raise ServiceError(f"Failed to get active session: {e}", e) from e

    def list_sessions(
        self,
        project: str,
        limit: int = 10,
        include_active: bool = True,
    ) -> list[Session]:
        """List sessions for a project.

        Args:
            project: The project name to filter by.
            limit: Maximum number of sessions to return.
            include_active: Whether to include active sessions.

        Returns:
            List of Session entities.

        Raises:
            ServiceError: If fetching sessions fails.
        """
        try:
            sessions = self._repository.get_recent(project, limit=limit)
            if not include_active:
                sessions = [s for s in sessions if s.ended_at is not None]
            return sessions
        except Exception as e:
            raise ServiceError(f"Failed to list sessions: {e}", e) from e
