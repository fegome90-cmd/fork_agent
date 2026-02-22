"""Get observation use case."""

from __future__ import annotations

from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository


class GetObservation:
    """Use case for getting a single observation."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def execute(self, observation_id: str) -> Observation:
        return self._repository.get_by_id(observation_id)
