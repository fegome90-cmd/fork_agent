"""Unit tests for Observation entity."""

from __future__ import annotations

import pytest

from src.domain.entities.observation import Observation


class TestObservation:
    """Tests for Observation entity."""

    def test_create_observation_with_required_fields(self) -> None:
        """Test creating observation with only required fields."""
        observation = Observation(
            id="test-id-001",
            timestamp=1700000000000,
            content="Test observation content",
        )

        assert observation.id == "test-id-001"
        assert observation.timestamp == 1700000000000
        assert observation.content == "Test observation content"
        assert observation.metadata is None

    def test_create_observation_with_metadata(self) -> None:
        """Test creating observation with metadata."""
        metadata = {"source": "test", "tags": ["python", "tdd"]}
        observation = Observation(
            id="test-id-002",
            timestamp=1700000000000,
            content="Observation with metadata",
            metadata=metadata,
        )

        assert observation.metadata == metadata

    def test_observation_is_immutable(self) -> None:
        """Test that observation cannot be modified after creation."""
        observation = Observation(
            id="test-id-003",
            timestamp=1700000000000,
            content="Immutable test",
        )

        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            observation.content = "modified"  # type: ignore[misc]

    def test_observation_validates_id_type(self) -> None:
        """Test that id must be a string."""
        with pytest.raises(TypeError, match="id must be a string"):
            Observation(
                id=123,  # type: ignore[arg-type]
                timestamp=1700000000000,
                content="test",
            )

    def test_observation_validates_id_not_empty(self) -> None:
        """Test that id cannot be empty."""
        with pytest.raises(ValueError, match="id must not be empty"):
            Observation(
                id="",
                timestamp=1700000000000,
                content="test",
            )

    def test_observation_validates_timestamp_type(self) -> None:
        """Test that timestamp must be an integer."""
        with pytest.raises(TypeError, match="timestamp must be an integer"):
            Observation(
                id="test-id",
                timestamp="not-an-int",  # type: ignore[arg-type]
                content="test",
            )

    def test_observation_validates_timestamp_not_negative(self) -> None:
        """Test that timestamp cannot be negative."""
        with pytest.raises(ValueError, match="timestamp must be non-negative"):
            Observation(
                id="test-id",
                timestamp=-1,
                content="test",
            )

    def test_observation_validates_content_type(self) -> None:
        """Test that content must be a string."""
        with pytest.raises(TypeError, match="content must be a string"):
            Observation(
                id="test-id",
                timestamp=1700000000000,
                content=123,  # type: ignore[arg-type]
            )

    def test_observation_validates_content_not_empty(self) -> None:
        """Test that content cannot be empty."""
        with pytest.raises(ValueError, match="content must not be empty"):
            Observation(
                id="test-id",
                timestamp=1700000000000,
                content="",
            )

    def test_observation_validates_metadata_type(self) -> None:
        """Test that metadata must be a dict or None."""
        with pytest.raises(TypeError, match="metadata must be a dict or None"):
            Observation(
                id="test-id",
                timestamp=1700000000000,
                content="test",
                metadata="not-a-dict",  # type: ignore[arg-type]
            )

    def test_observation_accepts_zero_timestamp(self) -> None:
        """Test that zero is a valid timestamp (Unix epoch start)."""
        observation = Observation(
            id="test-id",
            timestamp=0,
            content="epoch test",
        )

        assert observation.timestamp == 0

    def test_observation_accepts_empty_metadata_dict(self) -> None:
        """Test that empty dict is valid metadata."""
        observation = Observation(
            id="test-id",
            timestamp=1700000000000,
            content="test",
            metadata={},
        )

        assert observation.metadata == {}
