"""Task Board application service — business logic for orchestration tasks."""

from __future__ import annotations

import builtins  # noqa: F401 — needed because `def list()` shadows builtin
import dataclasses
import time
import uuid
from dataclasses import replace

from src.application.exceptions import TaskTransitionError
from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)
from src.domain.ports.fpel_authorization_port import FPELAuthorizationPort
from src.domain.ports.orchestration_task_repository import (
    OrchestrationTaskRepository,
)

_UNSET: object = object()


class TaskBoardService:
    """Application service coordinating orchestration task operations.

    All mutations produce new frozen instances via ``dataclasses.replace()``
    and persist through the injected repository.
    """

    __slots__ = ("_repo", "_fpel_port")

    def __init__(
        self,
        repo: OrchestrationTaskRepository,
        fpel_port: FPELAuthorizationPort | None = None,
    ) -> None:
        self._repo = repo
        self._fpel_port = fpel_port

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        subject: str,
        description: str | None = None,
        owner: str | None = None,
    ) -> OrchestrationTask:
        """Create a new PENDING task with a UUID4 identifier.

        Note: Rate limiting is not implemented for this single-user CLI tool.
        """
        now_ms = int(time.time() * 1000)
        task = OrchestrationTask(
            id=uuid.uuid4().hex,
            subject=subject,
            description=description,
            status=OrchestrationTaskStatus.PENDING,
            owner=owner,
            created_at=now_ms,
            updated_at=now_ms,
        )
        self._repo.save(task)
        return task

    def get(self, task_id: str) -> OrchestrationTask | None:
        """Retrieve a task by its ID."""
        return self._repo.get_by_id(task_id)

    def list(
        self,
        status: OrchestrationTaskStatus | None = None,
        owner: str | None = None,
        include_deleted: bool = False,
    ) -> list[OrchestrationTask]:
        """List tasks, optionally filtered by status and/or owner.

        By default, DELETED tasks are excluded unless ``include_deleted``
        is True. When a ``status`` filter is provided, ``include_deleted``
        is ignored — all matching tasks are returned regardless of deletion.
        """
        if status is not None and owner is not None:
            status_tasks = self._repo.list_by_status(status)
            return [t for t in status_tasks if t.owner == owner]
        if status is not None:
            return self._repo.list_by_status(status)
        if owner is not None:
            return self._repo.list_by_owner(owner)
        # Neither filter — use list_all and optionally filter DELETED.
        tasks = self._repo.list_all()
        if not include_deleted:
            tasks = [t for t in tasks if t.status != OrchestrationTaskStatus.DELETED]
        return tasks

    def update(
        self,
        task_id: str,
        subject: str | None = _UNSET,  # type: ignore[assignment]
        description: str | None = _UNSET,  # type: ignore[assignment]
        owner: str | None = _UNSET,  # type: ignore[assignment]
    ) -> OrchestrationTask:
        """Partially update a task's mutable fields.

        Returns a new frozen instance with updated fields and a fresh
        ``updated_at`` timestamp.  Only explicitly passed arguments are
        applied; omitted fields retain their current value (including None).
        """
        task = self._repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        if task.status == OrchestrationTaskStatus.DELETED:
            raise ValueError(f"Cannot update deleted task '{task_id}'")

        now_ms = int(time.time() * 1000)
        kwargs: dict[str, str | int | None] = {"updated_at": now_ms}
        if subject is not _UNSET:
            kwargs["subject"] = subject
        if description is not _UNSET:
            kwargs["description"] = description
        if owner is not _UNSET:
            kwargs["owner"] = owner

        updated = replace(task, **kwargs)  # type: ignore[arg-type]
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        return updated

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def submit_plan(
        self, task_id: str, plan_text: str, requested_by: str | None = None
    ) -> OrchestrationTask:
        """Transition PENDING -> PLANNING and attach the plan."""
        task = self._require_task(task_id)
        self._validate_transition(task, OrchestrationTaskStatus.PLANNING)

        now_ms = int(time.time() * 1000)
        updated = replace(
            task,
            status=OrchestrationTaskStatus.PLANNING,
            plan_text=plan_text,
            updated_at=now_ms,
            requested_by=requested_by,
        )
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        return updated

    def approve(
        self, task_id: str, approved_by: str, requested_by: str | None = None
    ) -> OrchestrationTask:
        """Transition PLANNING -> APPROVED."""
        task = self._require_task(task_id)
        self._validate_transition(task, OrchestrationTaskStatus.APPROVED)

        now_ms = int(time.time() * 1000)
        updated = replace(
            task,
            status=OrchestrationTaskStatus.APPROVED,
            approved_by=approved_by,
            approved_at=now_ms,
            updated_at=now_ms,
            requested_by=requested_by,
        )
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        return updated

    def reject(self, task_id: str, requested_by: str | None = None) -> OrchestrationTask:
        """Transition PLANNING -> PENDING, clearing the plan."""
        task = self._require_task(task_id)
        self._validate_transition(task, OrchestrationTaskStatus.PENDING)

        now_ms = int(time.time() * 1000)
        updated = replace(
            task,
            status=OrchestrationTaskStatus.PENDING,
            plan_text=None,
            updated_at=now_ms,
            requested_by=requested_by,
        )
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        return updated

    def start(self, task_id: str, owner: str, requested_by: str | None = None) -> OrchestrationTask:
        """Transition APPROVED -> IN_PROGRESS.

        If an FPELAuthorizationPort is injected, the task must have a
        sealed PASS for the current frozen hash before starting.

        Raises:
            ValueError: If the task is blocked by other tasks or lacks sealed PASS.
        """
        task = self._require_task(task_id)
        if task.is_blocked:
            raise ValueError(f"Task '{task_id}' is blocked by: {', '.join(task.blocked_by)}")
        self._validate_transition(task, OrchestrationTaskStatus.IN_PROGRESS)

        # FPEL gate: sealed PASS required for implementation start
        if self._fpel_port is not None:
            from src.infrastructure.persistence.fpel_content_hash import compute_task_hash

            current_hash = compute_task_hash(task)
            decision = self._fpel_port.check_sealed(task_id, current_hash=current_hash)
            if not decision.allowed:
                from src.application.exceptions import TaskTransitionError

                raise TaskTransitionError(
                    f"Task '{task_id}' requires sealed PASS to start. "
                    f"Status: {decision.status.value}"
                )

        now_ms = int(time.time() * 1000)
        updated = replace(
            task,
            status=OrchestrationTaskStatus.IN_PROGRESS,
            owner=owner,
            updated_at=now_ms,
            requested_by=requested_by,
        )
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        return updated

    def complete(self, task_id: str, requested_by: str | None = None) -> OrchestrationTask:
        """Transition IN_PROGRESS -> COMPLETED.

        Also resolves any blockers that depend on this task.
        """
        task = self._require_task(task_id)
        self._validate_transition(task, OrchestrationTaskStatus.COMPLETED)

        now_ms = int(time.time() * 1000)
        updated = replace(
            task,
            status=OrchestrationTaskStatus.COMPLETED,
            updated_at=now_ms,
            requested_by=requested_by,
        )
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        # Fire-and-forget blocker resolution.
        self.resolve_blockers(task_id)
        return updated

    def retry(self, task_id: str) -> OrchestrationTask:
        """Reset an IN_PROGRESS task back to APPROVED for re-processing.

        Used when a poll run fails or is cancelled — the task needs to go
        back to the approved pool so it can be picked up again.
        """
        task = self._repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        if not task.can_transition_to(OrchestrationTaskStatus.APPROVED):
            raise TaskTransitionError(
                f"Cannot retry task '{task_id}' in status {task.status.value}"
            )
        updated = dataclasses.replace(task, status=OrchestrationTaskStatus.APPROVED)
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently during retry")
        return updated

    def delete(self, task_id: str, requested_by: str | None = None) -> OrchestrationTask:
        """Soft-delete a task (any status -> DELETED)."""
        task = self._require_task(task_id)
        self._validate_transition(task, OrchestrationTaskStatus.DELETED)

        now_ms = int(time.time() * 1000)
        updated = replace(
            task,
            status=OrchestrationTaskStatus.DELETED,
            updated_at=now_ms,
            requested_by=requested_by,
        )
        if not self._repo.cas_save(updated, task.status):
            raise ValueError("Task was modified concurrently")
        return updated

    # ------------------------------------------------------------------
    # Blocker resolution
    # ------------------------------------------------------------------

    def resolve_blockers(self, task_id: str) -> builtins.list[str]:
        """After a task completes, find tasks now unblocked by it.

        Returns IDs of tasks whose *only* remaining blockers are
        COMPLETED or DELETED.
        """
        unblocked: list[str] = []

        for candidate in self._repo.list_blocked():
            if task_id not in candidate.blocked_by:
                continue

            # Batch-fetch all blockers for this candidate in one query.
            blockers = self._repo.get_by_ids(list(candidate.blocked_by))
            blocker_map: dict[str, OrchestrationTask] = {b.id: b for b in blockers}

            all_resolved = True
            for blocker_id in candidate.blocked_by:
                blocker = blocker_map.get(blocker_id)
                # Design decision: a nonexistent blocker is treated as
                # resolved (not as an error).  This handles the case where
                # a blocker was hard-deleted from the DB.
                # A blocker is unresolved only if it exists and is neither
                # COMPLETED nor DELETED.
                if blocker is not None and blocker.status not in (
                    OrchestrationTaskStatus.COMPLETED,
                    OrchestrationTaskStatus.DELETED,
                ):
                    all_resolved = False
                    break
            if all_resolved:
                unblocked.append(candidate.id)

        return unblocked

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_task(self, task_id: str) -> OrchestrationTask:
        """Fetch a task or raise ValueError."""
        task = self._repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task '{task_id}' not found")
        return task

    @staticmethod
    def _validate_transition(
        task: OrchestrationTask,
        target: OrchestrationTaskStatus,
    ) -> None:
        """Raise TaskTransitionError if the transition is not allowed."""
        if not task.can_transition_to(target):
            raise TaskTransitionError(
                f"Cannot transition task '{task.id}' from {task.status.value} to {target.value}"
            )
