"""Tests for TaskDecomposer service."""

from __future__ import annotations

import pytest

from src.application.services.workflow.task_decomposer import (
    CircularDependencyError,
    TaskDecomposer,
)
from src.domain.entities.derived_requirement import (
    DerivedRequirement,
    RequirementPriority,
    RequirementSource,
)
from src.domain.entities.goal import Goal


class TestTaskDecomposer:
    """Tests for TaskDecomposer."""

    def test_decompose_basic(self) -> None:
        """Test basic decomposition."""
        goal = Goal(objective="Build API", must_haves=("Auth",))
        requirements = [
            DerivedRequirement(
                id="auth",
                description="Authentication",
                source=RequirementSource.EXPLICIT,
                priority=RequirementPriority.MUST,
            )
        ]

        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(goal, requirements)

        assert len(tasks) > 0
        # First task should be foundation
        assert tasks[0].slug == "project-setup"
        # Last task should be the main goal task
        assert tasks[-1].slug == "build-api"

    def test_decompose_with_dependencies(self) -> None:
        """Test that tasks have proper dependencies."""
        goal = Goal(objective="Build API", must_haves=("Auth", "DB"))
        requirements = [
            DerivedRequirement(
                id="auth",
                description="Authentication",
                source=RequirementSource.EXPLICIT,
                priority=RequirementPriority.MUST,
            ),
            DerivedRequirement(
                id="db",
                description="Database",
                source=RequirementSource.EXPLICIT,
                priority=RequirementPriority.MUST,
            ),
        ]

        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(goal, requirements)

        # Find task IDs
        task_by_slug = {t.slug: t for t in tasks}

        # Core tasks should depend on setup
        setup_id = task_by_slug["project-setup"].id
        auth_task = task_by_slug["auth"]
        assert setup_id in auth_task.depends_on

    def test_decompose_validates_no_cycles(self) -> None:
        """Test that decomposition validates no circular dependencies."""
        Goal(objective="Test")

        # Create tasks directly to test validation
        decomposer = TaskDecomposer()
        tasks = [
            type(
                "Task",
                (),
                {
                    "id": "a",
                    "slug": "a",
                    "description": "a",
                    "depends_on": ("b",),
                },
            )(),
            type(
                "Task",
                (),
                {
                    "id": "b",
                    "slug": "b",
                    "description": "b",
                    "depends_on": ("a",),
                },
            )(),
        ]

        with pytest.raises(CircularDependencyError):
            decomposer._validate_dependencies(tasks)  # type: ignore[arg-type]

    def test_decompose_validates_no_self_reference(self) -> None:
        """Test that self-referencing tasks raise error."""
        decomposer = TaskDecomposer()

        from src.application.services.workflow.state import Task

        tasks = [Task(id="a", slug="a", description="a", depends_on=("a",))]

        with pytest.raises(CircularDependencyError):
            decomposer._validate_dependencies(tasks)

    def test_decompose_includes_nice_to_haves(self) -> None:
        """Test that nice-to-haves are included."""
        goal = Goal(
            objective="Build API",
            must_haves=("Auth",),
            nice_to_haves=("Docs",),
        )

        from src.application.services.workflow.goal_analyzer import GoalAnalyzer

        analyzer = GoalAnalyzer()
        requirements = analyzer.analyze(goal)

        decomposer = TaskDecomposer()
        tasks = decomposer.decompose(goal, requirements)

        # Should have optional tasks
        task_ids = [t.slug for t in tasks]
        assert "docs" in task_ids or any("doc" in t for t in task_ids)


class TestCircularDependencyError:
    """Tests for CircularDependencyError exception."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = CircularDependencyError("Test cycle")
        assert "cycle" in str(error).lower()
