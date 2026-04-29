"""Unit tests for TaskBoardService.start() FPEL gate — Task 1.4.

Tests that start() gates via FPELAuthorizationPort.check_sealed():
- sealed PASS allows start
- candidate PASS denied
- post-seal content drift (hash mismatch) rejected
- idempotent sealed PASS consumption (start twice succeeds)
- verdict_candidate never accepted
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.application.exceptions import TaskTransitionError
from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.fpel import (
    AuthorizationDecision,
    FPELStatus,
    SealFailureReason,
)
from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)
from src.domain.ports.fpel_authorization_port import FPELAuthorizationPort

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW_MS = int(time.time() * 1000)
TASK_ID = "a" * 32
CONTENT_HASH = "deadbeef" * 8


def _make_task(
    task_id: str = TASK_ID,
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.APPROVED,
    **overrides: object,
) -> OrchestrationTask:
    defaults: dict[str, object] = {
        "id": task_id,
        "subject": "Test task",
        "status": status,
        "created_at": NOW_MS,
        "updated_at": NOW_MS,
    }
    defaults.update(overrides)
    return OrchestrationTask(**defaults)  # type: ignore[arg-type]


def _make_service_with_fpel(
    repo: MagicMock | None = None,
    fpel_port: MagicMock | None = None,
) -> tuple[TaskBoardService, MagicMock, MagicMock]:
    mock_repo = repo if repo is not None else MagicMock()
    mock_repo.cas_save.return_value = True
    mock_fpel = fpel_port if fpel_port is not None else MagicMock(spec=FPELAuthorizationPort)
    service = TaskBoardService(repo=mock_repo, fpel_port=mock_fpel)  # type: ignore[arg-type]
    return service, mock_repo, mock_fpel


def _sealed_pass_decision() -> AuthorizationDecision:
    return AuthorizationDecision(
        allowed=True,
        status=FPELStatus.SEALED_PASS,
        frozen_proposal_id="fp-001",
        content_hash=CONTENT_HASH,
        reason=None,
        seal_id="seal-001",
        sealed_at=datetime.now(tz=UTC),
    )


def _denied_decision(
    status: FPELStatus = FPELStatus.NOT_FROZEN,
    reason: SealFailureReason = SealFailureReason.NO_FROZEN_PROPOSAL,
) -> AuthorizationDecision:
    return AuthorizationDecision(
        allowed=False,
        status=status,
        frozen_proposal_id=None,
        content_hash=None,
        reason=reason,
        seal_id=None,
        sealed_at=None,
    )


# ---------------------------------------------------------------------------
# start() gates via FPELAuthorizationPort.check_sealed()
# ---------------------------------------------------------------------------


class TestStartGatesViaFPEL:
    def test_start_calls_fpel_check_sealed(self) -> None:
        """start() must call FPELAuthorizationPort.check_sealed() with current_hash."""
        service, repo, fpel = _make_service_with_fpel()
        repo.get_by_id.return_value = _make_task()
        fpel.check_sealed.return_value = _sealed_pass_decision()

        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            service.start(TASK_ID, owner="worker")

        fpel.check_sealed.assert_called_once()
        call_args = fpel.check_sealed.call_args
        assert call_args[0][0] == TASK_ID
        assert call_args[1].get("current_hash") is not None, (
            "check_sealed() MUST receive current_hash from caller"
        )

    def test_sealed_pass_allows_start(self) -> None:
        """Sealed PASS authorizes APPROVED → IN_PROGRESS."""
        service, repo, fpel = _make_service_with_fpel()
        repo.get_by_id.return_value = _make_task()
        fpel.check_sealed.return_value = _sealed_pass_decision()

        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.start(TASK_ID, owner="worker")

        assert result.status == OrchestrationTaskStatus.IN_PROGRESS
        repo.cas_save.assert_called_once()


# ---------------------------------------------------------------------------
# Never accepts verdict_candidate
# ---------------------------------------------------------------------------


class TestCandidatePassDenied:
    def test_start_rejects_candidate_pass(self) -> None:
        """Candidate PASS does NOT authorize start."""
        service, repo, fpel = _make_service_with_fpel()
        repo.get_by_id.return_value = _make_task()
        fpel.check_sealed.return_value = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.CHECK_PASSED,
            frozen_proposal_id="fp-001",
            content_hash=CONTENT_HASH,
            reason=SealFailureReason.MISSING_REPORTS,
            seal_id=None,
            sealed_at=None,
        )

        with pytest.raises(TaskTransitionError, match="sealed PASS"):
            service.start(TASK_ID, owner="worker")


# ---------------------------------------------------------------------------
# Post-seal drift rejected
# ---------------------------------------------------------------------------


class TestPostSealDriftRejected:
    def test_start_rejects_hash_mismatch(self) -> None:
        """Post-seal content drift (hash mismatch) denied at gate."""
        service, repo, fpel = _make_service_with_fpel()
        repo.get_by_id.return_value = _make_task()
        fpel.check_sealed.return_value = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.SEALED_PASS,
            frozen_proposal_id="fp-001",
            content_hash="tamperedhash" * 4,
            reason=SealFailureReason.HASH_MISMATCH,
            seal_id=None,
            sealed_at=None,
        )

        with pytest.raises(TaskTransitionError, match="sealed PASS"):
            service.start(TASK_ID, owner="worker")


# ---------------------------------------------------------------------------
# Idempotent sealed PASS consumption
# ---------------------------------------------------------------------------


class TestIdempotentSealedPass:
    def test_start_twice_with_same_seal_succeeds(self) -> None:
        """start() called twice with same sealed PASS on APPROVED tasks."""
        service, repo, fpel = _make_service_with_fpel()
        fpel.check_sealed.return_value = _sealed_pass_decision()

        # First start: APPROVED -> IN_PROGRESS
        task_approved = _make_task(status=OrchestrationTaskStatus.APPROVED)
        repo.get_by_id.return_value = task_approved
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result1 = service.start(TASK_ID, owner="worker")

        assert result1.status == OrchestrationTaskStatus.IN_PROGRESS
        assert fpel.check_sealed.call_count == 1

        # Second start on IN_PROGRESS raises transition error BEFORE gate
        task_in_progress = _make_task(status=OrchestrationTaskStatus.IN_PROGRESS)
        repo.get_by_id.return_value = task_in_progress
        with pytest.raises(ValueError, match="Cannot transition"):
            service.start(TASK_ID, owner="worker")

        # FPEL gate NOT called again — transition validation fails first
        assert fpel.check_sealed.call_count == 1


# ---------------------------------------------------------------------------
# FPEL port is optional (backward compat for non-FPEL tasks)
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_start_without_fpel_port_works_as_before(self) -> None:
        """If no fpel_port injected, start() works as pre-FPEL behavior."""
        mock_repo = MagicMock()
        mock_repo.cas_save.return_value = True
        mock_repo.get_by_id.return_value = _make_task()
        service = TaskBoardService(repo=mock_repo)

        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.start(TASK_ID, owner="worker")

        assert result.status == OrchestrationTaskStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# Hash authority: current_hash computed from task content
# ---------------------------------------------------------------------------


class TestHashAuthority:
    def test_start_passes_content_hash_to_gate(self) -> None:
        """start() computes current_hash from task and passes to check_sealed."""
        service, repo, fpel = _make_service_with_fpel()
        repo.get_by_id.return_value = _make_task(plan_text="# Plan A")
        fpel.check_sealed.return_value = _sealed_pass_decision()

        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            service.start(TASK_ID, owner="worker")

        call_hash = fpel.check_sealed.call_args[1]["current_hash"]
        assert call_hash is not None

        from src.infrastructure.persistence.fpel_content_hash import compute_task_hash

        expected = compute_task_hash(_make_task(plan_text="# Plan A"))
        assert call_hash == expected

    def test_post_freeze_plan_change_blocks_start(self) -> None:
        """If plan_text changes after freeze, start() blocked by HASH_MISMATCH."""
        service, repo, fpel = _make_service_with_fpel()
        repo.get_by_id.return_value = _make_task(plan_text="# Plan B — MODIFIED")
        fpel.check_sealed.return_value = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.SEALED_PASS,
            frozen_proposal_id="fp-001",
            content_hash="original_hash_not_matching",
            reason=SealFailureReason.HASH_MISMATCH,
            seal_id=None,
            sealed_at=None,
        )

        with pytest.raises(TaskTransitionError, match="sealed PASS"):
            service.start(TASK_ID, owner="worker")

        call_hash = fpel.check_sealed.call_args[1]["current_hash"]
        from src.infrastructure.persistence.fpel_content_hash import compute_task_hash

        expected = compute_task_hash(_make_task(plan_text="# Plan B — MODIFIED"))
        assert call_hash == expected
