"""Search observations use case."""

from __future__ import annotations

from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository


class SearchObservations:
    """Use case for searching observations."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def execute(self, query: str, limit: int | None = None) -> list[Observation]:
        return self._repository.search(query, limit=limit)
