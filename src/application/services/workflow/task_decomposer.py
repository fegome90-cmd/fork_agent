"""Task decomposition service for breaking goals into ordered tasks."""

from __future__ import annotations

import uuid

from src.application.services.workflow.state import Task
from src.domain.entities.derived_requirement import DerivedRequirement, RequirementPriority
from src.domain.entities.goal import Goal


def slugify(text: str) -> str:
    """Convert text to a slug-friendly identifier."""
    import re

    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text


class CircularDependencyError(Exception):
    """Raised when task dependencies form a cycle."""

    pass


class TaskDecomposer:
    """Decomposes goals into ordered tasks with dependency tracking."""

    def decompose(
        self,
        goal: Goal,
        requirements: list[DerivedRequirement],
    ) -> list[Task]:
        """Decompose goal into ordered tasks.

        Args:
            goal: The goal to decompose.
            requirements: The requirements derived from the goal.

        Returns:
            Ordered list of tasks with dependencies.

        Raises:
            CircularDependencyError: If circular dependencies are detected.
        """
        tasks: list[Task] = []

        # Separate must-have vs nice-to-have requirements
        must_reqs = [r for r in requirements if r.priority == RequirementPriority.MUST]
        nice_reqs = [r for r in requirements if r.priority == RequirementPriority.NICE]

        # Phase 1: Foundation tasks (setup, config)
        foundation_tasks = self._create_foundation_tasks(goal)
        tasks.extend(foundation_tasks)

        # Phase 2: Core tasks (from must-have requirements)
        core_tasks = self._create_core_tasks(must_reqs, foundation_tasks)
        tasks.extend(core_tasks)

        # Phase 3: Integration tasks
        integration_tasks = self._create_integration_tasks(goal, core_tasks)
        tasks.extend(integration_tasks)

        # Phase 4: Optional tasks (nice-to-haves)
        if nice_reqs:
            optional_tasks = self._create_optional_tasks(nice_reqs, core_tasks)
            tasks.extend(optional_tasks)

        # Phase 5: Add the main task
        main_task = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            slug=slugify(goal.objective),
            description=goal.objective,
            status="pending",
            requirement_ids=tuple(r.id for r in requirements),
            depends_on=tuple(t.id for t in core_tasks if t.id),
        )
        tasks.append(main_task)

        # CRITICAL: Validate no circular dependencies
        self._validate_dependencies(tasks)

        return tasks

    def _create_foundation_tasks(self, goal: Goal) -> list[Task]:
        """Create foundation/setup tasks."""
        tasks = []

        # Task: Project setup
        setup_task = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            slug="project-setup",
            description="Set up project structure and dependencies",
            status="pending",
            depends_on=(),
            requirement_ids=(),
        )
        tasks.append(setup_task)

        return tasks

    def _create_core_tasks(
        self,
        requirements: list[DerivedRequirement],
        foundation_tasks: list[Task],
    ) -> list[Task]:
        """Create core tasks from requirements."""
        tasks = []
        foundation_ids = tuple(t.id for t in foundation_tasks)

        for req in requirements:
            task = Task(
                id=f"task-{uuid.uuid4().hex[:8]}",
                slug=req.id,
                description=req.description,
                status="pending",
                depends_on=foundation_ids,
                requirement_ids=(req.id,),
            )
            tasks.append(task)

        return tasks

    def _create_integration_tasks(
        self,
        goal: Goal,
        core_tasks: list[Task],
    ) -> list[Task]:
        """Create integration tasks."""
        tasks = []

        if not core_tasks:
            return tasks

        core_ids = tuple(t.id for t in core_tasks)

        # Integration task - depends on all core tasks
        integration_task = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            slug="integration",
            description="Integrate components and verify functionality",
            status="pending",
            depends_on=core_ids,
            requirement_ids=(),
        )
        tasks.append(integration_task)

        return tasks

    def _create_optional_tasks(
        self,
        requirements: list[DerivedRequirement],
        core_tasks: list[Task],
    ) -> list[Task]:
        """Create optional/nice-to-have tasks."""
        tasks = []

        if not core_tasks:
            return tasks

        # These depend on integration being complete
        integration_id = core_tasks[-1].id if core_tasks else None
        depends_on = (integration_id,) if integration_id else ()

        for req in requirements:
            task = Task(
                id=f"task-{uuid.uuid4().hex[:8]}",
                slug=req.id,
                description=req.description,
                status="pending",
                depends_on=depends_on,
                requirement_ids=(req.id,),
            )
            tasks.append(task)

        return tasks

    def _validate_dependencies(self, tasks: list[Task]) -> None:
        """Validate no circular or self-referential dependencies.

        Args:
            tasks: List of tasks to validate.

        Raises:
            CircularDependencyError: If circular or self-referential dependencies found.
        """
        # Build dependency graph
        dep_graph: dict[str, set[str]] = {}
        for task in tasks:
            dep_graph[task.id] = set(task.depends_on)

        # Check for self-reference
        for task in tasks:
            if task.id in dep_graph[task.id]:
                raise CircularDependencyError(f"Task '{task.id}' depends on itself")

        # Check for cycles using DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in dep_graph.get(node, set()):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    raise CircularDependencyError(
                        f"Circular dependency detected involving task '{task.id}'"
                    )
