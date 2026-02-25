"""Tests for Goal entity."""

from __future__ import annotations

import pytest

from src.domain.entities.goal import Goal


class TestGoal:
    """Tests for Goal entity."""

    def test_goal_creation_minimal(self) -> None:
        """Test creating a goal with only objective."""
        goal = Goal(objective="Build an API")
        assert goal.objective == "Build an API"
        assert goal.must_haves == ()
        assert goal.nice_to_haves == ()
        assert goal.scope_in == ()
        assert goal.scope_out == ()

    def test_goal_creation_full(self) -> None:
        """Test creating a goal with all fields."""
        goal = Goal(
            objective="Build a payment API",
            must_haves=("Stripe", "PCI compliance"),
            nice_to_haves=("Refunds", "Analytics"),
            scope_in=("backend",),
            scope_out=("frontend", "mobile"),
        )
        assert goal.objective == "Build a payment API"
        assert goal.must_haves == ("Stripe", "PCI compliance")
        assert goal.nice_to_haves == ("Refunds", "Analytics")
        assert goal.scope_in == ("backend",)
        assert goal.scope_out == ("frontend", "mobile")

    def test_goal_immutable(self) -> None:
        """Test that goal is immutable (frozen=True)."""
        goal = Goal(objective="Test")
        with pytest.raises(AttributeError):
            goal.objective = "New objective"

    def test_goal_empty_objective_raises(self) -> None:
        """Test that empty objective raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Goal(objective="")

    def test_goal_non_string_objective_raises(self) -> None:
        """Test that non-string objective raises TypeError."""
        with pytest.raises(TypeError):
            Goal(objective=123)  # type: ignore[arg-type]

    def test_goal_max_length(self) -> None:
        """Test that very long objective raises ValueError."""
        long_objective = "x" * 10001
        with pytest.raises(ValueError, match="10000"):
            Goal(objective=long_objective)

    def test_goal_scope_overlap_raises(self) -> None:
        """Test that overlapping scope_in and scope_out raises ValueError."""
        with pytest.raises(ValueError, match="disjoint"):
            Goal(
                objective="Test",
                scope_in=("backend",),
                scope_out=("backend",),
            )

    def test_goal_collections_must_be_tuples(self) -> None:
        """Test that collections must be tuples."""
        with pytest.raises(TypeError):
            Goal(objective="Test", must_haves=["not", "tuple"])  # type: ignore[arg-type]
