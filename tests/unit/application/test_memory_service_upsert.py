"""Tests for MemoryService upsert via topic_key."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)


class TestMemoryServiceUpsert:
    """Tests for MemoryService.save() with topic_key upsert."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=ObservationRepository)

    def test_save_with_topic_key_creates_when_not_exists(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        mock_repository.get_by_topic_key.return_value = None

        service = MemoryService(repository=mock_repository)
        observation = service.save(
            content="First save",
            topic_key="fork/my-change/proposal",
        )

        assert observation.content == "First save"
        assert observation.topic_key == "fork/my-change/proposal"
        mock_repository.create.assert_called_once()
        mock_repository.update.assert_not_called()

    def test_save_with_topic_key_updates_when_exists(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        existing = Observation(
            id="existing-id-001",
            timestamp=1700000000000,
            content="Old content",
            metadata={"topic_key": "fork/my-change/proposal"},
            topic_key="fork/my-change/proposal",
        )
        mock_repository.get_by_topic_key.return_value = existing

        upserted = Observation(
            id="existing-id-001",
            timestamp=1700000001000,
            content="Updated content",
            metadata={"topic_key": "fork/my-change/proposal", "extra": "data"},
            topic_key="fork/my-change/proposal",
        )
        mock_repository.upsert_topic_key.return_value = upserted

        service = MemoryService(repository=mock_repository)
        observation = service.save(
            content="Updated content",
            metadata={"topic_key": "fork/my-change/proposal", "extra": "data"},
            topic_key="fork/my-change/proposal",
        )

        assert observation.id == "existing-id-001"
        assert observation.content == "Updated content"
        assert observation.topic_key == "fork/my-change/proposal"
        mock_repository.upsert_topic_key.assert_called_once()
        mock_repository.create.assert_not_called()

    def test_save_without_topic_key_always_creates(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        service = MemoryService(repository=mock_repository)
        observation = service.save(content="No topic_key")

        assert observation.content == "No topic_key"
        assert observation.topic_key is None
        mock_repository.create.assert_called_once()

    def test_save_without_metadata_always_creates(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        service = MemoryService(repository=mock_repository)
        observation = service.save(content="No metadata at all", metadata=None)

        assert observation.content == "No metadata at all"
        mock_repository.create.assert_called_once()

    def test_save_with_topic_key_preserves_id_on_update(self, mock_repository: MagicMock) -> None:
        from src.application.services.memory_service import MemoryService

        existing = Observation(
            id="original-uuid",
            timestamp=1700000000000,
            content="Old",
            topic_key="fork/test/key",
        )
        mock_repository.get_by_topic_key.return_value = existing

        upserted = Observation(
            id="original-uuid",
            timestamp=1700000001000,
            content="New content",
            topic_key="fork/test/key",
        )
        mock_repository.upsert_topic_key.return_value = upserted

        service = MemoryService(repository=mock_repository)
        observation = service.save(
            content="New content",
            topic_key="fork/test/key",
        )

        assert observation.id == "original-uuid"
        mock_repository.upsert_topic_key.assert_called_once()
