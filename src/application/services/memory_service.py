"""Memory service for observation business logic."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)

if TYPE_CHECKING:
    from src.application.services.telemetry.telemetry_service import TelemetryService


class MemoryService:
    """Service for managing observations with business logic."""

    __slots__ = ("_repository", "_telemetry")

    def __init__(
        self,
        repository: ObservationRepository,
        telemetry_service: TelemetryService | None = None,
    ) -> None:
        self._repository = repository
        self._telemetry = telemetry_service

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

        # Track telemetry if available
        if self._telemetry:
            self._telemetry.track_memory_save(
                observation_id=observation.id,
                content_length=len(content),
                has_metadata=metadata is not None,
            )

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
        start_ms = int(time.time() * 1000)
        results = self._repository.search(query, limit=limit)
        duration_ms = int(time.time() * 1000) - start_ms

        # Track telemetry if available
        if self._telemetry:
            self._telemetry.track_memory_search(
                query_length=len(query),
                limit=limit or 10,
                results_count=len(results),
                duration_ms=duration_ms,
            )

        return results

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

        # Track telemetry if available
        if self._telemetry:
            self._telemetry.track_memory_delete(observation_id=observation_id)

    def get_by_time_range(self, start: int, end: int) -> list[Observation]:
        return self._repository.get_by_timestamp_range(start, end)

    def query(
        self,
        agent: str | None = None,
        run_id: str | None = None,
        event_type: str | None = None,
        limit: int = 20,
        scan_limit: int = 1000,
        since_ms: int | None = None,
    ) -> list[Observation]:
        """Query memory events with structured filters.

        Args:
            agent: Filter by agent ID or from_agent_id.
            run_id: Filter by run ID.
            event_type: Filter by event type.
            limit: Maximum results to return.
            scan_limit: Maximum observations to scan from DB.
            since_ms: Time filter (Unix ms).

        Returns:
            List of matching observations, sorted by timestamp DESC.
        """
        # Fetch observations with scan_limit (safety)
        observations = self._repository.get_all(limit=scan_limit, offset=0)

        # Filter by agent_id or from_agent_id
        if agent:
            filtered = []
            for obs in observations:
                if not obs.metadata:
                    continue
                agent_id = obs.metadata.get("agent_id", "")
                from_agent = obs.metadata.get("extra", {}).get("from_agent_id", "")
                if agent in agent_id or agent in from_agent:
                    filtered.append(obs)
            observations = filtered

        # Filter by run_id
        if run_id:
            observations = [
                obs
                for obs in observations
                if obs.metadata and obs.metadata.get("run_id") == run_id
            ]

        # Filter by event_type
        if event_type:
            observations = [
                obs
                for obs in observations
                if obs.metadata and obs.metadata.get("event_type") == event_type
            ]

        # Filter by time (since)
        if since_ms:
            observations = [
                obs for obs in observations if obs.timestamp >= since_ms
            ]

        # Sort by timestamp DESC
        observations.sort(key=lambda o: o.timestamp, reverse=True)

        # Apply limit
        return observations[:limit]
