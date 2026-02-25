"""Unit tests for MemoryService.

TDD Red Phase: These tests define the expected behavior BEFORE implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)


class TestMemoryServiceSave:
    """Tests for MemoryService.save operation."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_save_creates_observation_with_id(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        service = MemoryService(repository=mock_repository)
        observation = service.save(content="Test observation")

        assert observation.id is not None
        assert observation.content == "Test observation"
        mock_repository.create.assert_called_once()

    def test_save_with_metadata(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        service = MemoryService(repository=mock_repository)
        observation = service.save(
            content="Observation with metadata",
            metadata={"source": "test", "tags": ["python"]},
        )

        assert observation.metadata == {"source": "test", "tags": ["python"]}

    def test_save_generates_timestamp(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        service = MemoryService(repository=mock_repository)
        observation = service.save(content="Timestamp test")

        assert observation.timestamp > 0


class TestMemoryServiceSearch:
    """Tests for MemoryService.search operation."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_search_returns_matching_observations(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.search.return_value = [
            Observation(id="1", timestamp=1000, content="Python code"),
            Observation(id="2", timestamp=2000, content="Python test"),
        ]

        service = MemoryService(repository=mock_repository)
        results = service.search("Python")

        assert len(results) == 2
        mock_repository.search.assert_called_once_with("Python", limit=None)

    def test_search_with_limit(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.search.return_value = [
            Observation(id="1", timestamp=1000, content="test"),
        ]

        service = MemoryService(repository=mock_repository)
        service.search("test", limit=5)

        mock_repository.search.assert_called_once_with("test", limit=5)

    def test_search_returns_empty_list_when_no_match(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.search.return_value = []

        service = MemoryService(repository=mock_repository)
        results = service.search("nonexistent")

        assert results == []


class TestMemoryServiceGetRecent:
    """Tests for MemoryService.get_recent operation."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_get_recent_returns_latest_observations(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.get_all.return_value = [
            Observation(id="3", timestamp=3000, content="Third"),
            Observation(id="2", timestamp=2000, content="Second"),
            Observation(id="1", timestamp=1000, content="First"),
        ]

        service = MemoryService(repository=mock_repository)
        results = service.get_recent(limit=10)

        assert len(results) == 3
        assert results[0].timestamp == 3000

    def test_get_recent_with_limit(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.get_all.return_value = [
            Observation(id="3", timestamp=3000, content="Third"),
            Observation(id="2", timestamp=2000, content="Second"),
        ]

        service = MemoryService(repository=mock_repository)
        results = service.get_recent(limit=2)

        assert len(results) == 2


class TestMemoryServiceGetById:
    """Tests for MemoryService.get_by_id operation."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_get_by_id_returns_observation(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.get_by_id.return_value = Observation(
            id="test-id",
            timestamp=1000,
            content="Test content",
        )

        service = MemoryService(repository=mock_repository)
        result = service.get_by_id("test-id")

        assert result.id == "test-id"
        assert result.content == "Test content"

    def test_get_by_id_raises_not_found(self, mock_repository: MagicMock) -> None:
        from src.application.exceptions import ObservationNotFoundError
        from src.application.services.memory_service import MemoryService

        mock_repository.get_by_id.side_effect = ObservationNotFoundError("Not found")

        service = MemoryService(repository=mock_repository)

        with pytest.raises(ObservationNotFoundError):
            service.get_by_id("nonexistent")


class TestMemoryServiceDelete:
    """Tests for MemoryService.delete operation."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_delete_removes_observation(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        service = MemoryService(repository=mock_repository)
        service.delete("test-id")

        mock_repository.delete.assert_called_once_with("test-id")


class TestMemoryServiceGetByTimeRange:
    """Tests for MemoryService.get_by_time_range operation."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_get_by_time_range_returns_observations(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.get_by_timestamp_range.return_value = [
            Observation(id="2", timestamp=2000, content="Second"),
            Observation(id="1", timestamp=1000, content="First"),
        ]

        service = MemoryService(repository=mock_repository)
        results = service.get_by_time_range(start=1000, end=2000)

        assert len(results) == 2
        mock_repository.get_by_timestamp_range.assert_called_once_with(1000, 2000)
