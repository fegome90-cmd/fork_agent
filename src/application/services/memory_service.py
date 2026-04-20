"""Memory service for observation business logic."""

from __future__ import annotations

import dataclasses
import time
import uuid
from typing import TYPE_CHECKING, Any

from src.application.services.redaction import redact_observation_data
from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository

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
        topic_key: str | None = None,
        project: str | None = None,
        type: str | None = None,
        title: str | None = None,
    ) -> Observation:
        # Redact PII before storage (covers all entrypoints: MCP, CLI, import, compact)
        content, metadata, _was_redacted = redact_observation_data(content, metadata)

        existing_for_topic = None
        if topic_key:
            existing_for_topic = self._repository.get_by_topic_key(topic_key, project=project)

        observation = Observation(
            id=str(uuid.uuid4()),
            timestamp=int(time.time() * 1000),
            content=content,
            title=title,
            metadata=metadata,
            topic_key=topic_key,
            project=project,
            type=type,
        )

        if existing_for_topic is not None:
            observation = self._repository.upsert_topic_key(observation)
        else:
            self._repository.create(observation)

        if self._telemetry:
            self._telemetry.track_memory_save(
                observation_id=observation.id,
                content_length=len(content),
                has_metadata=metadata is not None,
            )

        return observation

    def update(
        self,
        observation_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        type: str | None = None,
        topic_key: str | None = None,
        project: str | None = None,
        title: str | None = None,
    ) -> Observation:
        # Redact PII before update (covers all entrypoints)
        if content is not None or metadata is not None:
            redacted_content, redacted_metadata, _was_redacted = redact_observation_data(
                content or "", metadata
            )
            if content is not None:
                content = redacted_content
            if metadata is not None:
                metadata = redacted_metadata

        existing = self._repository.get_by_id(observation_id)

        updates: dict[str, Any] = {"revision_count": existing.revision_count + 1}
        if content is not None:
            updates["content"] = content
            if metadata is not None:
                updates["metadata"] = metadata
        elif metadata is not None:
            updates["metadata"] = metadata
        if type is not None:
            updates["type"] = type
        if topic_key is not None:
            updates["topic_key"] = topic_key
        if project is not None:
            updates["project"] = project
        if title is not None:
            updates["title"] = title

        updated = dataclasses.replace(existing, **updates)
        self._repository.update(updated)
        return updated

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

    def search(self, query: str, limit: int | None = None, project: str | None = None) -> list[Observation]:
        start_ms = int(time.time() * 1000)
        results = self._repository.search(query, limit=limit, project=project)
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

    def get_recent(
        self,
        limit: int = 10,
        offset: int = 0,
        type: str | None = None,
        project: str | None = None,
    ) -> list[Observation]:
        """Get recent observations with pagination.

        Args:
            limit: Maximum number of observations to return. Must be >= 0.
            offset: Number of observations to skip. Must be >= 0.
            type: Optional type filter to narrow results.
            project: Optional project filter to narrow results.

        Returns:
            List of observations.

        Raises:
            ValueError: If limit or offset are negative.
        """
        if limit < 0:
            raise ValueError(f"limit must be >= 0, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")

        return self._repository.get_all(limit=limit, offset=offset, type=type, project=project)

    def get_by_id(self, observation_id: str) -> Observation:
        return self._repository.get_by_id(observation_id)

    def get_by_id_prefix(self, prefix: str) -> list[Observation]:
        """Get observations that match the given ID prefix."""
        return self._repository.get_by_id_prefix(prefix)

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
                obs for obs in observations if obs.metadata and obs.metadata.get("run_id") == run_id
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
            observations = [obs for obs in observations if obs.timestamp >= since_ms]

        # Sort by timestamp DESC
        observations.sort(key=lambda o: o.timestamp, reverse=True)

        # Apply limit
        return observations[:limit]

    def save_prompt(
        self,
        content: str,
        project: str | None = None,
        session_id: str | None = None,
        role: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> int:
        if session_id is not None:
            effective_session = session_id
        elif project is not None:
            effective_session = f"manual-save-{project}"
        else:
            effective_session = None
        return self._repository.save_prompt(
            content=content,
            session_id=effective_session,
            role=role,
            model=model,
            provider=provider,
        )

    def merge_projects(self, from_projects: str, to_project: str) -> dict[str, Any]:
        canonical = self._normalize_project_name(to_project)
        if not canonical:
            return {
                "canonical": "",
                "sources_merged": [],
                "observations_updated": 0,
                "sessions_updated": 0,
            }
        sources = [self._normalize_project_name(s) for s in from_projects.split(",")]
        sources = [s for s in sources if s and s != canonical]
        if not sources:
            return {
                "canonical": canonical,
                "sources_merged": [],
                "observations_updated": 0,
                "sessions_updated": 0,
            }
        return self._repository.merge_projects(canonical=canonical, sources=sources)

    @staticmethod
    def _normalize_project_name(name: str) -> str:
        return name.strip().lower().rstrip("/")
