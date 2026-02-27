"""Memory service for observation business logic."""

from __future__ import annotations

import time
import uuid
from typing import Any

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)


class MemoryService:
    """Service for managing observations with business logic."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def save(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Observation:
        observation = Observation(
            id=str(uuid.uuid4()),
            timestamp=int(time.time() * 1000),
            content=content,
            metadata=metadata,
        )
        self._repository.create(observation)
        return observation

    def save_event(
        self,
        content: str,
        metadata: dict[str, Any],
        idempotency_key: str,
    ) -> str:
        """Save a structured event observation with idempotency guarantee.

        This method is designed for structured events (workflow, agents, etc.)
        and guarantees idempotency via the idempotency_key.

        If an event with the same idempotency_key already exists, this is a no-op
        and returns the existing observation ID.

        Args:
            content: Event content/description
            metadata: Event metadata (should follow MemoryEventMetadata contract)
            idempotency_key: Unique key for deduplication

        Returns:
            The observation ID (existing or new)

        Example:
            >>> from src.application.services.memory.event_metadata import (
            ...     create_event_metadata, EventType, ExecutionMode
            ... )
            >>> meta = create_event_metadata(
            ...     event_type=EventType.AGENT_SPAWNED,
            ...     run_id="run-123",
            ...     task_id="task-456",
            ...     agent_id="agent:0",
            ...     session_name="session-1",
            ...     mode=ExecutionMode.WORKTREE,
            ... )
            >>> obs_id = memory.save_event(
            ...     content="Agent spawned in worktree",
            ...     metadata=meta.model_dump(),
            ...     idempotency_key=meta.idempotency_key,
            ... )
        """
        return self._repository.save_event(
            content=content,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    def search(self, query: str, limit: int | None = None) -> list[Observation]:
        return self._repository.search(query, limit=limit)

    def get_recent(self, limit: int = 10, offset: int = 0) -> list[Observation]:
        """Get recent observations with pagination.

        Args:
            limit: Maximum number of observations to return. Must be >= 0.
            offset: Number of observations to skip. Must be >= 0.

        Returns:
            List of observations.

        Raises:
            ValueError: If limit or offset are negative.
        """
        if limit < 0:
            raise ValueError(f"limit must be >= 0, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")

        return self._repository.get_all(limit=limit, offset=offset)

    def get_by_id(self, observation_id: str) -> Observation:
        return self._repository.get_by_id(observation_id)

    def delete(self, observation_id: str) -> None:
        self._repository.delete(observation_id)

    def get_by_time_range(self, start: int, end: int) -> list[Observation]:
        return self._repository.get_by_timestamp_range(start, end)
