"""Delete observation use case."""

from __future__ import annotations

from src.domain.ports.observation_repository import ObservationRepository


class DeleteObservation:
    """Use case for deleting an observation."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def execute(self, observation_id: str) -> None:
        self._repository.delete(observation_id)
