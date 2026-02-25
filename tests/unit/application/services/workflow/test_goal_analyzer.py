"""Tests for GoalAnalyzer service."""

from __future__ import annotations

import pytest

from src.domain.entities.goal import Goal
from src.domain.entities.derived_requirement import (
    DerivedRequirement,
    RequirementPriority,
    RequirementSource,
)
from src.application.services.workflow.goal_analyzer import (
    GoalAnalyzer,
    GoalAnalysisError,
    slugify,
)


class TestSlugify:
    """Tests for slugify helper."""

    def test_slugify_simple(self) -> None:
        """Test simple text slugification."""
        assert slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self) -> None:
        """Test slugification with special characters."""
        assert slugify("Test @#$!") == "test"

    def test_slugify_underscores(self) -> None:
        """Test slugification with underscores."""
        assert slugify("hello_world-test") == "hello-world-test"


class TestGoalAnalyzer:
    """Tests for GoalAnalyzer."""

    def test_analyze_none_goal_returns_empty(self) -> None:
        """Test that None goal returns empty list (backward compat)."""
        analyzer = GoalAnalyzer()
        result = analyzer.analyze(None)
        assert result == []

    def test_analyze_with_must_haves(self) -> None:
        """Test analysis with explicit must-haves."""
        goal = Goal(
            objective="Build API",
            must_haves=("Authentication", "CRUD"),
        )
        analyzer = GoalAnalyzer()
        result = analyzer.analyze(goal)

        assert len(result) >= 2
        auth_req = next(r for r in result if r.id == "authentication")
        assert auth_req.source == RequirementSource.EXPLICIT
        assert auth_req.priority == RequirementPriority.MUST

    def test_analyze_with_nice_to_haves(self) -> None:
        """Test analysis with nice-to-haves."""
        goal = Goal(
            objective="Build API",
            nice_to_haves=("Rate limiting",),
        )
        analyzer = GoalAnalyzer()
        result = analyzer.analyze(goal)

        rate_req = next(r for r in result if r.id == "rate-limiting")
        assert rate_req.priority == RequirementPriority.NICE

    def test_analyze_derives_implicit_requirements(self) -> None:
        """Test that implicit requirements are derived from keywords."""
        goal = Goal(
            objective="Build a REST API with authentication",
            must_haves=("JWT",),
        )
        analyzer = GoalAnalyzer()
        result = analyzer.analyze(goal)

        # Should have both explicit and derived
        ids = [r.id for r in result]
        assert "jwt" in ids
        # Derived from "API"
        assert "error-handling" in ids
        # Derived from "authentication"
        assert "password-hashing" in ids

    def test_analyze_no_requirements_raises(self) -> None:
        """Test that analysis with no requirements raises error."""
        goal = Goal(objective="Do something")
        analyzer = GoalAnalyzer()

        with pytest.raises(GoalAnalysisError):
            analyzer.analyze(goal)

    def test_analyze_deduplicates_explicit_and_derived(self) -> None:
        """Test that explicit requirements aren't duplicated as derived."""
        goal = Goal(
            objective="Build an API with error handling",
            must_haves=("Error handling",),  # Explicit
        )
        analyzer = GoalAnalyzer()
        result = analyzer.analyze(goal)

        # Should not have duplicate error-handling
        error_reqs = [r for r in result if r.id == "error-handling"]
        assert len(error_reqs) == 1
        assert error_reqs[0].source == RequirementSource.EXPLICIT

    def test_analyze_empty_objective(self) -> None:
        """Test that empty objective with must-haves works."""
        goal = Goal(objective="", must_haves=("Test",))
        analyzer = GoalAnalyzer()
        result = analyzer.analyze(goal)

        assert len(result) == 1
        assert result[0].id == "test"
