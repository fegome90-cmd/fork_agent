"""Unified retrieval search service."""

from __future__ import annotations

from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository
from src.infrastructure.retrieval.v2.enhanced_search import EnhancedRetrievalSearchService


class RetrievalSearchService:
    __slots__ = ("_repository", "_enhanced")

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository
        self._enhanced = EnhancedRetrievalSearchService(repository)

    def search(
        self,
        query: str,
        limit: int | None = None,
        project: str | None = None,
        type_: str | None = None,
        session_id: str | None = None,
    ) -> list[Observation]:
        return self._enhanced.search(
            query, limit=limit, project=project, type=type_, session_id=session_id
        )
