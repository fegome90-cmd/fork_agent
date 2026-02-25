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

    def search(self, query: str, limit: int | None = None) -> list[Observation]:
        return self._repository.search(query, limit=limit)

    def get_recent(self, limit: int = 10) -> list[Observation]:
        all_observations = self._repository.get_all()
        return all_observations[:limit]

    def get_by_id(self, observation_id: str) -> Observation:
        return self._repository.get_by_id(observation_id)

    def delete(self, observation_id: str) -> None:
        self._repository.delete(observation_id)

    def get_by_time_range(self, start: int, end: int) -> list[Observation]:
        return self._repository.get_by_timestamp_range(start, end)
