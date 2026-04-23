from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

_TRANSITIONS: dict[OrchestrationTaskStatus, set[OrchestrationTaskStatus]] = {}


class OrchestrationTaskStatus(StrEnum):
    """Orchestration task status enum with string values for database persistence."""

    PENDING = "PENDING"
    PLANNING = "PLANNING"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELETED = "DELETED"


# Build transition map after class definition.
_TRANSITIONS = {
    OrchestrationTaskStatus.PENDING: {
        OrchestrationTaskStatus.PLANNING,
        OrchestrationTaskStatus.DELETED,
    },
    OrchestrationTaskStatus.PLANNING: {
        OrchestrationTaskStatus.APPROVED,
        OrchestrationTaskStatus.PENDING,
        OrchestrationTaskStatus.DELETED,
    },
    OrchestrationTaskStatus.APPROVED: {
        OrchestrationTaskStatus.IN_PROGRESS,
        OrchestrationTaskStatus.DELETED,
    },
    OrchestrationTaskStatus.IN_PROGRESS: {
        OrchestrationTaskStatus.COMPLETED,
        OrchestrationTaskStatus.DELETED,
    },
    OrchestrationTaskStatus.COMPLETED: {
        OrchestrationTaskStatus.DELETED,
    },
    OrchestrationTaskStatus.DELETED: set(),
}


@dataclass(frozen=True)
class OrchestrationTask:
    """Immutable orchestration task entity.

    Represents a task in the task board lifecycle: creation through
    planning, approval, execution, and completion.

    Attributes:
        id: Unique identifier for the task (UUID string).
        subject: Short title / summary of the task.
        description: Optional longer description.
        status: Current lifecycle status.
        owner: Agent or user responsible for the task.
        blocked_by: Tuple of task IDs this task is blocked by.
        plan_text: Optional plan content produced during PLANNING phase.
        created_at: Unix timestamp in milliseconds when task was created.
        updated_at: Unix timestamp in milliseconds of last update.
        approved_by: Who approved the task (set on APPROVED transition).
        approved_at: Unix timestamp in milliseconds when task was approved.
    """

    id: str
    subject: str
    description: str | None = None
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.PENDING
    owner: str | None = None
    blocked_by: tuple[str, ...] = ()
    plan_text: str | None = None
    created_at: int = 0
    updated_at: int = 0
    approved_by: str | None = None
    approved_at: int | None = None
    requested_by: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id must be a string")
        if not self.id:
            raise ValueError("id must not be empty")
        if not isinstance(self.subject, str):
            raise TypeError("subject must be a string")
        if not self.subject:
            raise ValueError("subject must not be empty")
        if self.description is not None and not isinstance(self.description, str):
            raise TypeError("description must be a string or None")
        if not isinstance(self.status, OrchestrationTaskStatus):
            raise TypeError("status must be an OrchestrationTaskStatus")
        if self.owner is not None and not isinstance(self.owner, str):
            raise TypeError("owner must be a string or None")
        if not isinstance(self.blocked_by, tuple):
            raise TypeError("blocked_by must be a tuple of strings")
        if self.id in self.blocked_by:
            raise ValueError(f"Task '{self.id}' cannot block itself")
        for task_id in self.blocked_by:
            if not isinstance(task_id, str):
                raise TypeError("each blocked_by entry must be a string")
            if not task_id:
                raise ValueError("blocked_by entries must not be empty")
        if self.plan_text is not None and not isinstance(self.plan_text, str):
            raise TypeError("plan_text must be a string or None")
        if not isinstance(self.created_at, int):
            raise TypeError("created_at must be an integer")
        if self.created_at < 0:
            raise ValueError("created_at must be non-negative")
        if not isinstance(self.updated_at, int):
            raise TypeError("updated_at must be an integer")
        if self.updated_at < 0:
            raise ValueError("updated_at must be non-negative")
        if self.approved_by is not None and not isinstance(self.approved_by, str):
            raise TypeError("approved_by must be a string or None")
        if self.approved_at is not None and not isinstance(self.approved_at, int):
            raise TypeError("approved_at must be an integer or None")

    def can_transition_to(self, target: OrchestrationTaskStatus) -> bool:
        """Check whether a transition from the current status to *target* is valid.

        Args:
            target: The desired next status.

        Returns:
            True if the transition is allowed, False otherwise.
        """
        return target in _TRANSITIONS.get(self.status, set())

    @staticmethod
    def detect_cycle(all_tasks: list[OrchestrationTask]) -> bool:
        """Detect cycles in the blocked_by graph using DFS.

        Given a list of tasks, returns True if any cycle exists in the
        dependency graph (A→B→C→A).  Intended for batch validation rather
        than per-entity construction (too expensive for ``__post_init__``).
        """
        index: dict[str, OrchestrationTask] = {t.id: t for t in all_tasks}
        visited: set[str] = set()
        stack: set[str] = set()

        def _dfs(task_id: str) -> bool:
            if task_id in stack:
                return True
            if task_id in visited:
                return False
            visited.add(task_id)
            stack.add(task_id)
            task = index.get(task_id)
            if task is not None:
                for dep_id in task.blocked_by:
                    if _dfs(dep_id):
                        return True
            stack.discard(task_id)
            return False

        return any(_dfs(t.id) for t in all_tasks)

    @property
    def is_blocked(self) -> bool:
        """Whether this task is blocked by other tasks."""
        return len(self.blocked_by) > 0
