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

    def update(self, observation: Observation) -> None: ...

    def save_event(self, content: str, metadata: dict[str, Any], idempotency_key: str) -> str: ...

    def get_by_idempotency_key(self, idempotency_key: str) -> Observation | None: ...

    def save_prompt(
        self,
        content: str,
        session_id: str | None,
        role: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> int: ...

    def merge_projects(
        self,
        canonical: str,
        sources: list[str],
    ) -> dict[str, Any]: ...
