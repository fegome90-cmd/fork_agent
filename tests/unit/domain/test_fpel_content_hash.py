"""Tests for FPEL content hash computation at call sites.

Verifies that:
1. OrchestrationTask has a stable canonical hash
2. PlanState has a stable canonical hash
3. Changes to fields produce different hashes
4. Same content produces same hash (idempotent)
"""

from src.application.services.workflow.state import PlanState, Task, WorkflowPhase
from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)
from src.infrastructure.persistence.fpel_content_hash import (
    compute_plan_hash,
    compute_task_hash,
)


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

        # Simulate post-freeze change
        from dataclasses import replace

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
        from dataclasses import replace

        task = OrchestrationTask(
            id="t-001",
            subject="Add auth",
            plan_text="# Plan",
            status=OrchestrationTaskStatus.APPROVED,
        )
        h_approved = compute_task_hash(task)
        task_in_progress = replace(task, status=OrchestrationTaskStatus.IN_PROGRESS)
        h_in_progress = compute_task_hash(task_in_progress)
        # Status change should NOT change hash — content hasn't changed
        assert h_approved == h_in_progress


class TestComputePlanHash:
    """PlanState canonical hash computation."""

    def test_stable_hash_same_plan(self) -> None:
        """Same plan always produces same hash."""
        plan = PlanState(
            session_id="sess-001",
            phase=WorkflowPhase.OUTLINED,
            tasks=[
                Task(id="t-001", slug="auth", description="Add JWT"),
            ],
        )
        h1 = compute_plan_hash(plan)
        h2 = compute_plan_hash(plan)
        assert h1 == h2

    def test_different_tasks_different_hash(self) -> None:
        """Changed tasks produce different hash."""
        plan_a = PlanState(
            session_id="sess-001",
            phase=WorkflowPhase.OUTLINED,
            tasks=[Task(id="t-001", slug="auth", description="Add JWT")],
        )
        plan_b = PlanState(
            session_id="sess-001",
            phase=WorkflowPhase.OUTLINED,
            tasks=[Task(id="t-001", slug="auth", description="Add OAuth")],
        )
        assert compute_plan_hash(plan_a) != compute_plan_hash(plan_b)

    def test_post_freeze_drift_detected(self) -> None:
        """If tasks change after freeze, hash drift is detected."""
        plan = PlanState(
            session_id="sess-001",
            phase=WorkflowPhase.OUTLINED,
            tasks=[Task(id="t-001", slug="auth", description="JWT")],
        )
        frozen_hash = compute_plan_hash(plan)

        modified = PlanState(
            session_id="sess-001",
            phase=WorkflowPhase.OUTLINED,
            tasks=[Task(id="t-001", slug="auth", description="JWT + OAuth")],
        )
        current_hash = compute_plan_hash(modified)

        assert frozen_hash != current_hash, "Drift MUST be detected"

    def test_empty_plan_stable_hash(self) -> None:
        """Empty plan (no tasks) produces stable hash."""
        plan = PlanState(
            session_id="sess-empty",
            phase=WorkflowPhase.PLANNING,
            tasks=[],
        )
        h = compute_plan_hash(plan)
        assert isinstance(h, str)
        assert len(h) == 64
