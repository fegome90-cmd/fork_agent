from __future__ import annotations

from unittest.mock import MagicMock

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.repositories.observation_repository import ObservationRepository


def test_memory_service_search_uses_retrieval_pipeline() -> None:
    from src.application.services.memory_service import MemoryService

    repository = MagicMock(spec=ObservationRepository)
    expected = Observation(id='1', timestamp=1, content='branch review procedure', metadata={'type': 'procedure'})

    repository.search.return_value = [expected]

    service = MemoryService(repository=repository)
    results = service.search('how do I kick off branch review from cli sessions', limit=3)

    assert results == [expected]
    assert repository.search.call_count >= 1
