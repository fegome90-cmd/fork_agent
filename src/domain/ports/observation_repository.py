"""Ports (Protocols) for IO operations."""

from __future__ import annotations

from typing import Any, Protocol

from src.domain.entities.observation import Observation


class ObservationRepository(Protocol):
    """Protocol for observation persistence."""

    def create(self, observation: Observation) -> None: ...

    def get_by_id(self, observation_id: str) -> Observation: ...

    def get_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
        type: str | None = None,
    ) -> list[Observation]: ...

    def search(self, query: str, limit: int | None) -> list[Observation]: ...

    def delete(self, observation_id: str) -> None: ...

    def get_by_timestamp_range(self, start: int, end: int) -> list[Observation]: ...

    def get_by_topic_key(
        self, topic_key: str, project: str | None = None
    ) -> Observation | None: ...

    def upsert_topic_key(self, observation: Observation) -> Observation: ...

    def update(
        self,
        observation_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        type: str | None = None,
        topic_key: str | None = None,
        project: str | None = None,
    ) -> Observation: ...
