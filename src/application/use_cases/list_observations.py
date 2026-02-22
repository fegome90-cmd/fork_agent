"""List observations use case."""

from __future__ import annotations

from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository


class ListObservations:
    """Use case for listing recent observations."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def execute(self, limit: int = 10) -> list[Observation]:
        all_observations = self._repository.get_all()
        return all_observations[:limit]
