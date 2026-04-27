"""Tests for IN_PROGRESS -> APPROVED retry transition (SM-C1/C2)."""

from __future__ import annotations

from src.domain.entities.orchestration_task import OrchestrationTask, OrchestrationTaskStatus


class TestRetryTransition:
    def test_in_progress_can_transition_to_approved(self) -> None:
        """IN_PROGRESS -> APPROVED must be valid for retry."""
        task = OrchestrationTask(
            id="t1",
            subject="test",
            status=OrchestrationTaskStatus.IN_PROGRESS,
        )
        assert task.can_transition_to(OrchestrationTaskStatus.APPROVED)

    def test_completed_cannot_transition_to_approved(self) -> None:
        """COMPLETED -> APPROVED should still be invalid."""
        task = OrchestrationTask(
            id="t1",
            subject="test",
            status=OrchestrationTaskStatus.COMPLETED,
        )
        assert not task.can_transition_to(OrchestrationTaskStatus.APPROVED)

    def test_approved_cannot_transition_to_approved(self) -> None:
        """APPROVED -> APPROVED is a no-op, not a valid transition."""
        task = OrchestrationTask(
            id="t1",
            subject="test",
            status=OrchestrationTaskStatus.APPROVED,
        )
        assert not task.can_transition_to(OrchestrationTaskStatus.APPROVED)

    def test_pending_cannot_transition_to_approved(self) -> None:
        """PENDING -> APPROVED is not a valid direct transition."""
        task = OrchestrationTask(
            id="t1",
            subject="test",
            status=OrchestrationTaskStatus.PENDING,
        )
        assert not task.can_transition_to(OrchestrationTaskStatus.APPROVED)
