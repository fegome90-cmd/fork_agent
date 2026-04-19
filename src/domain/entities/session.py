"""Session entity for session lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Session:
    """Immutable session entity for session lifecycle management.

    Represents a work session with metadata for context recovery.

    Attributes:
        id: Unique identifier for the session.
        project: Project name associated with the session.
        directory: Working directory path.
        started_at: Unix timestamp in milliseconds when session started.
        ended_at: Unix timestamp in milliseconds when session ended (None if active).
        goal: Optional goal description for the session.
        instructions: Optional instructions/constraints for the session.
        summary: Optional summary of what was accomplished.
    """

    id: str
    project: str
    directory: str
    started_at: int
    ended_at: int | None
    goal: str | None
    instructions: str | None
    summary: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id must be a string")
        if not self.id:
            raise ValueError("id cannot be empty")
        if not isinstance(self.project, str):
            raise TypeError("project must be a string")
        if not self.project:
            raise ValueError("project cannot be empty")
        if not isinstance(self.directory, str):
            raise TypeError("directory must be a string")
        if not self.directory:
            raise ValueError("directory cannot be empty")
        if not isinstance(self.started_at, int):
            raise TypeError("started_at must be an integer")
        if self.started_at < 0:
            raise ValueError("started_at must be non-negative")
        if self.ended_at is not None and not isinstance(self.ended_at, int):
            raise TypeError("ended_at must be an integer or None")
        if self.ended_at is not None and self.ended_at < 0:
            raise ValueError("ended_at must be non-negative")
        if self.goal is not None and not isinstance(self.goal, str):
            raise TypeError("goal must be a string or None")
        if self.instructions is not None and not isinstance(self.instructions, str):
            raise TypeError("instructions must be a string or None")
        if self.summary is not None and not isinstance(self.summary, str):
            raise TypeError("summary must be a string or None")

    def is_active(self) -> bool:
        """Check if the session is still active (not ended)."""
        return self.ended_at is None

    def duration_ms(self) -> int | None:
        """Get session duration in milliseconds.

        Returns:
            Duration in milliseconds, or None if session is still active.
        """
        if self.ended_at is None:
            return None
        return self.ended_at - self.started_at

    def to_metadata(self) -> dict[str, Any]:
        """Convert session to metadata dictionary."""
        return {
            "session_id": self.id,
            "project": self.project,
            "directory": self.directory,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "goal": self.goal,
            "instructions": self.instructions,
            "summary": self.summary,
        }
