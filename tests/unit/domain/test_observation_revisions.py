"""Unit tests for Observation revision_count field."""

from __future__ import annotations

import pytest

from src.domain.entities.observation import Observation


class TestObservationRevisionCount:
    """Tests for Observation revision_count field."""

    def test_create_observation_with_default_revision_count(self) -> None:
        """Test that revision_count defaults to 1."""
        observation = Observation(
            id="test-id-001",
            timestamp=1700000000000,
            content="Test observation content",
        )
        assert observation.revision_count == 1

    def test_create_observation_with_custom_revision_count(self) -> None:
        """Test creating observation with custom revision count."""
        observation = Observation(
            id="test-id-002",
            timestamp=1700000000000,
            content="Test observation content",
            revision_count=5,
        )
        assert observation.revision_count == 5

    def test_observation_revision_count_is_immutable(self) -> None:
        """Test that revision_count cannot be modified after creation."""
        observation = Observation(
            id="test-id-003",
            timestamp=1700000000000,
            content="Immutable test",
            revision_count=3,
        )
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            observation.revision_count = 10  # type: ignore[misc]

    def test_observation_validates_revision_count_type(self) -> None:
        """Test that revision_count must be an integer."""
        with pytest.raises(TypeError, match="revision_count must be an integer"):
            Observation(
                id="test-id",
                timestamp=1700000000000,
                content="test",
                revision_count="not-an-int",  # type: ignore[arg-type]
            )

    def test_observation_validates_revision_count_not_zero(self) -> None:
        """Test that revision_count cannot be zero."""
        with pytest.raises(ValueError, match="revision_count must be at least 1"):
            Observation(
                id="test-id",
                timestamp=1700000000000,
                content="test",
                revision_count=0,
            )

    def test_observation_validates_revision_count_not_negative(self) -> None:
        """Test that revision_count cannot be negative."""
        with pytest.raises(ValueError, match="revision_count must be at least 1"):
            Observation(
                id="test-id",
                timestamp=1700000000000,
                content="test",
                revision_count=-5,
            )

    def test_observation_accepts_minimum_revision_count(self) -> None:
        """Test that minimum valid revision_count is 1."""
        observation = Observation(
            id="test-id",
            timestamp=1700000000000,
            content="test",
            revision_count=1,
        )
        assert observation.revision_count == 1

    def test_observation_revision_count_included_in_equality(self) -> None:
        """Test that revision_count is considered in equality comparison."""
        obs1 = Observation(
            id="test-id",
            timestamp=1700000000000,
            content="test",
            revision_count=1,
        )
        obs2 = Observation(
            id="test-id",
            timestamp=1700000000000,
            content="test",
            revision_count=2,
        )
        assert obs1 != obs2
