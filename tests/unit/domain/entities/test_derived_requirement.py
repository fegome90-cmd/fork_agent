"""Tests for DerivedRequirement entity."""

from __future__ import annotations

import pytest

from src.domain.entities.derived_requirement import (
    DerivedRequirement,
    RequirementPriority,
    RequirementSource,
)


class TestDerivedRequirement:
    """Tests for DerivedRequirement entity."""

    def test_requirement_creation(self) -> None:
        """Test creating a derived requirement."""
        req = DerivedRequirement(
            id="test-req",
            description="Test requirement",
            source=RequirementSource.EXPLICIT,
            priority=RequirementPriority.MUST,
        )
        assert req.id == "test-req"
        assert req.description == "Test requirement"
        assert req.source == RequirementSource.EXPLICIT
        assert req.priority == RequirementPriority.MUST

    def test_requirement_immutable(self) -> None:
        """Test that requirement is immutable (frozen=True)."""
        req = DerivedRequirement(
            id="test",
            description="Test",
            source=RequirementSource.EXPLICIT,
            priority=RequirementPriority.MUST,
        )
        with pytest.raises(AttributeError):
            req.id = "new-id"

    def test_requirement_empty_id_raises(self) -> None:
        """Test that empty id raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            DerivedRequirement(
                id="",
                description="Test",
                source=RequirementSource.EXPLICIT,
                priority=RequirementPriority.MUST,
            )

    def test_requirement_empty_description_raises(self) -> None:
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            DerivedRequirement(
                id="test",
                description="",
                source=RequirementSource.EXPLICIT,
                priority=RequirementPriority.MUST,
            )

    def test_requirement_invalid_source_raises(self) -> None:
        """Test that invalid source raises TypeError."""
        with pytest.raises(TypeError):
            DerivedRequirement(
                id="test",
                description="Test",
                source="invalid",  # type: ignore[arg-type]
                priority=RequirementPriority.MUST,
            )

    def test_requirement_invalid_priority_raises(self) -> None:
        """Test that invalid priority raises TypeError."""
        with pytest.raises(TypeError):
            DerivedRequirement(
                id="test",
                description="Test",
                source=RequirementSource.EXPLICIT,
                priority="invalid",  # type: ignore[arg-type]
            )


class TestRequirementEnums:
    """Tests for Requirement enums."""

    def test_priority_values(self) -> None:
        """Test RequirementPriority enum values."""
        assert RequirementPriority.MUST.value == "must"
        assert RequirementPriority.NICE.value == "nice"

    def test_source_values(self) -> None:
        """Test RequirementSource enum values."""
        assert RequirementSource.EXPLICIT.value == "explicit"
        assert RequirementSource.DERIVED.value == "derived"
