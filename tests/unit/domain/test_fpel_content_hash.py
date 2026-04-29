"""Tests for FPEL content hash computation — canonical hash functions.

Verifies that:
1. OrchestrationTask has a stable canonical hash
2. Plan task list has a stable canonical hash
3. Single plan task hash is stable and scope-correct
4. Changes to fields produce different hashes
5. Same content produces same hash (idempotent)
"""

from dataclasses import replace

from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)
from src.domain.services.fpel_content_hash import (
    compute_plan_hash_from_tasks,
    compute_plan_task_hash,
    compute_task_hash,
)


def _task_dict(tid: str = "t-001", slug: str = "auth", desc: str = "Add JWT") -> dict[str, str]:
    return {"id": tid, "slug": slug, "description": desc}


class TestComputeTaskHash:
    """OrchestrationTask canonical hash computation."""

    def test_stable_hash_same_task(self) -> None:
        """Same task data always produces same hash."""
        task = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            description="Implement JWT auth",
            status=OrchestrationTaskStatus.APPROVED,
            plan_text="# Plan\n1. Add middleware\n2. Add tests",
        )
        h1 = compute_task_hash(task)
        h2 = compute_task_hash(task)
        assert h1 == h2

    def test_different_content_different_hash(self) -> None:
        """Changed plan_text produces different hash."""
        task_a = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            status=OrchestrationTaskStatus.APPROVED,
            plan_text="# Plan A",
        )
        task_b = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            status=OrchestrationTaskStatus.APPROVED,
            plan_text="# Plan B — CHANGED",
        )
        assert compute_task_hash(task_a) != compute_task_hash(task_b)

    def test_post_freeze_drift_detected(self) -> None:
        """If plan_text changes after freeze, hash drift is detected."""
        task = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            status=OrchestrationTaskStatus.APPROVED,
            plan_text="# Original plan",
        )
        frozen_hash = compute_task_hash(task)
        modified = replace(task, plan_text="# Modified plan")
        current_hash = compute_task_hash(modified)
        assert frozen_hash != current_hash, "Drift MUST be detected"

    def test_no_plan_text_uses_subject_and_description(self) -> None:
        """When plan_text is None, hash uses subject + description."""
        task = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            description="JWT middleware",
            status=OrchestrationTaskStatus.APPROVED,
        )
        h = compute_task_hash(task)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_status_change_does_not_change_hash(self) -> None:
        """Hash is content-based, not status-based."""
        task = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            plan_text="# Plan",
            status=OrchestrationTaskStatus.APPROVED,
        )
        h_approved = compute_task_hash(task)
        task_in_progress = replace(task, status=OrchestrationTaskStatus.IN_PROGRESS)
        h_in_progress = compute_task_hash(task_in_progress)
        assert h_approved == h_in_progress


class TestComputePlanHashFromTasks:
    """Plan task-list canonical hash computation."""

    def test_stable_hash_same_tasks(self) -> None:
        h1 = compute_plan_hash_from_tasks([_task_dict()])
        h2 = compute_plan_hash_from_tasks([_task_dict()])
        assert h1 == h2

    def test_different_tasks_different_hash(self) -> None:
        ha = compute_plan_hash_from_tasks([_task_dict(desc="Add JWT")])
        hb = compute_plan_hash_from_tasks([_task_dict(desc="Add OAuth")])
        assert ha != hb

    def test_post_freeze_drift_detected(self) -> None:
        frozen = compute_plan_hash_from_tasks([_task_dict(desc="JWT")])
        current = compute_plan_hash_from_tasks([_task_dict(desc="JWT + OAuth")])
        assert frozen != current, "Drift MUST be detected"

    def test_empty_plan_stable_hash(self) -> None:
        h = compute_plan_hash_from_tasks([])
        assert isinstance(h, str)
        assert len(h) == 64


class TestComputePlanTaskHash:
    """Single plan task hash — used for task-scoped targets."""

    def test_stable_hash(self) -> None:
        h1 = compute_plan_task_hash("t-1", "auth", "Add JWT")
        h2 = compute_plan_task_hash("t-1", "auth", "Add JWT")
        assert h1 == h2

    def test_different_description_different_hash(self) -> None:
        ha = compute_plan_task_hash("t-1", "auth", "JWT")
        hb = compute_plan_task_hash("t-1", "auth", "OAuth")
        assert ha != hb

    def test_task_hash_differs_from_plan_hash(self) -> None:
        """Task-level hash ≠ plan-level hash (different scope)."""
        td = _task_dict()
        task_hash = compute_plan_task_hash(td["id"], td["slug"], td["description"])
        plan_hash = compute_plan_hash_from_tasks([td])
        assert task_hash != plan_hash, "Task hash MUST differ from plan hash (scope isolation)"
