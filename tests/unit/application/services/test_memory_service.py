"""Unit tests for MemoryService update/save/get_recent with new fields.

TDD Red Phase: These tests define the expected behavior BEFORE implementation.
Phase 3 tasks: 3.1 (RED) → 3.2/3.3/3.4 (GREEN)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.exceptions import ObservationNotFoundError
from src.domain.entities.observation import Observation
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)


@pytest.fixture
def mock_repo() -> MagicMock:
    """Create a mock ObservationRepository."""
    repo = MagicMock(spec=ObservationRepository)
    repo.get_by_topic_key.return_value = None  # Default: no existing observation
    return repo


@pytest.fixture
def service(mock_repo: MagicMock):
    """Create a MemoryService with mock repository."""
    from src.application.services.memory_service import MemoryService

    return MemoryService(repository=mock_repo)


def _make_observation(**overrides) -> Observation:
    """Helper to create a test Observation with sensible defaults."""
    defaults = dict(
        id="obs-001",
        timestamp=1700000000000,
        content="Original content",
        metadata={"key": "value"},
        idempotency_key=None,
        project=None,
        type=None,
        topic_key=None,
        revision_count=1,
        session_id=None,
    )
    defaults.update(overrides)
    return Observation(**defaults)


# ============================================================
# Task 3.2: update() method tests
# ============================================================


class TestMemoryServiceUpdate:
    """Tests for MemoryService.update() method."""

    def test_update_content_returns_updated_observation(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """update(content="new") returns updated observation with new content."""
        existing = _make_observation()
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", content="new content")

        assert result.content == "new content"
        mock_repo.update.assert_called_once()

    def test_update_metadata_returns_updated_observation(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """update(metadata={"k": "v"}) returns updated observation with new metadata."""
        existing = _make_observation()
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", metadata={"new_key": "new_val"})

        assert result.metadata == {"new_key": "new_val"}
        mock_repo.update.assert_called_once()

    def test_update_type_returns_updated_observation(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """update(type="decision") returns updated observation with new type."""
        existing = _make_observation()
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", type="decision")

        assert result.type == "decision"
        mock_repo.update.assert_called_once()

    def test_update_topic_key_returns_updated_observation(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """update(topic_key="key") returns updated observation with new topic_key."""
        existing = _make_observation()
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", topic_key="my/topic")

        assert result.topic_key == "my/topic"
        mock_repo.update.assert_called_once()

    def test_update_project_returns_updated_observation(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """update(project="proj") returns updated observation with new project."""
        existing = _make_observation()
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", project="myproj")

        assert result.project == "myproj"
        mock_repo.update.assert_called_once()

    def test_update_increments_revision_count(self, service: object, mock_repo: MagicMock) -> None:
        """update() increments revision_count by 1."""
        existing = _make_observation(revision_count=3)
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", content="changed")

        assert result.revision_count == 4

    def test_update_raises_not_found_for_missing_observation(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """update() raises ObservationNotFoundError for missing observation."""
        mock_repo.get_by_id.side_effect = ObservationNotFoundError("Not found")

        with pytest.raises(ObservationNotFoundError):
            service.update("nonexistent-id", content="anything")

    def test_update_preserves_unchanged_fields(self, service: object, mock_repo: MagicMock) -> None:
        """update() only changes the fields passed; others stay the same."""
        existing = _make_observation(
            content="original",
            metadata={"k": "v"},
            type="decision",
            project="myproj",
        )
        mock_repo.get_by_id.return_value = existing

        result = service.update("obs-001", content="new content")

        assert result.content == "new content"
        assert result.metadata == {"k": "v"}
        assert result.type == "decision"
        assert result.project == "myproj"
        assert result.revision_count == 2

    def test_update_with_multiple_fields(self, service: object, mock_repo: MagicMock) -> None:
        """update() can update multiple fields at once."""
        existing = _make_observation()
        mock_repo.get_by_id.return_value = existing

        result = service.update(
            "obs-001",
            content="new",
            type="bugfix",
            project="proj",
        )

        assert result.content == "new"
        assert result.type == "bugfix"
        assert result.project == "proj"
        assert result.revision_count == 2


# ============================================================
# Task 3.3: save() with topic_key/project/type params
# ============================================================


class TestMemoryServiceSaveWithTopicKey:
    """Tests for MemoryService.save() with topic_key, project, type params."""

    def test_save_with_topic_key_calls_upsert(self, service: object, mock_repo: MagicMock) -> None:
        """save("content", topic_key="key") creates new observation."""
        result = service.save("test content", topic_key="my/topic")

        mock_repo.get_by_topic_key.assert_called_once()
        mock_repo.create.assert_called_once()
        assert result.topic_key == "my/topic"

    def test_save_with_topic_key_and_project(self, service: object, mock_repo: MagicMock) -> None:
        """save("content", topic_key="key", project="proj") creates Observation with project."""
        service.save("test content", topic_key="my/topic", project="myproj")

        call_args = mock_repo.create.call_args[0][0]
        assert call_args.topic_key == "my/topic"
        assert call_args.project == "myproj"

    def test_save_with_topic_key_and_type(self, service: object, mock_repo: MagicMock) -> None:
        """save("content", topic_key="key", type="decision") creates Observation with type."""
        service.save("test content", topic_key="my/topic", type="decision")

        call_args = mock_repo.create.call_args[0][0]
        assert call_args.type == "decision"
        assert call_args.topic_key == "my/topic"

    def test_save_without_topic_key_calls_create(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """save() without topic_key still uses create (backward compat)."""
        result = service.save("plain content")

        mock_repo.create.assert_called_once()
        mock_repo.upsert_topic_key.assert_not_called()
        assert result.content == "plain content"
        assert result.topic_key is None


# ============================================================
# Task 3.4: get_recent(type=) filter
# ============================================================


class TestMemoryServiceGetRecentWithTypeFilter:
    """Tests for MemoryService.get_recent() with type parameter."""

    def test_get_recent_with_type_calls_repo_with_type(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """get_recent(type="decision") calls repo.get_all(type="decision")."""
        mock_repo.get_all.return_value = [
            _make_observation(type="decision"),
        ]

        results = service.get_recent(type="decision")

        call_kwargs = mock_repo.get_all.call_args
        assert call_kwargs.kwargs.get("type") == "decision"
        assert len(results) == 1

    def test_get_recent_without_type_calls_repo_no_filter(
        self, service: object, mock_repo: MagicMock
    ) -> None:
        """get_recent() without type calls repo.get_all() with no type filter."""
        mock_repo.get_all.return_value = [
            _make_observation(),
            _make_observation(id="obs-002", content="second"),
        ]

        results = service.get_recent()

        call_kwargs = mock_repo.get_all.call_args
        assert call_kwargs.kwargs.get("type") is None
        assert len(results) == 2
