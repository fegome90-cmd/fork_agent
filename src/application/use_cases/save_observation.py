"""Save observation use case."""

from __future__ import annotations

import time
import uuid
from typing import Any

from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository


class SaveObservation:
    """Use case for saving a new observation."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def execute(
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
