"""Shared short ID resolution helper for CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.exceptions import ObservationNotFoundError

if TYPE_CHECKING:
    from src.application.services.memory_service import MemoryService


def resolve_observation_id(
    memory_service: MemoryService,
    observation_id: str,
) -> Any:
    """Resolve an observation ID, supporting short ID prefix matching.

    Tries exact match first, then prefix scan against all observations.
    Raises ObservationNotFoundError if no match, ValueError if ambiguous.
    """
    try:
        return memory_service.get_by_id(observation_id)
    except ObservationNotFoundError:
        all_obs = memory_service._repository.get_all()
        matches = [o for o in all_obs if o.id.startswith(observation_id)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous ID '{observation_id}' matches {len(matches)} observations"
            ) from None
        raise ObservationNotFoundError(
            f"Observation not found: {observation_id}"
        ) from None
