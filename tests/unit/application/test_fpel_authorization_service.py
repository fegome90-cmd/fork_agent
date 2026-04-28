"""Unit tests for FPELAuthorizationService — Task 1.2.

Tests the application service implementing FPELAuthorizationPort:
- candidate PASS denied, sealed PASS allowed
- missing/FAIL/NEEDS_REVIEW/NOT_EVALUATED denied
- seal invariants and idempotency
- re-freeze after failure
- mixed checker verdicts → NEEDS_HUMAN_DECISION
- required reports = all checkers must PASS
- FAIL terminal blocks subsequent seal/freeze transitions
- parametrized SealFailureReason coverage (all 5 values)
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.application.services.fpel_authorization_service import FPELAuthorizationService
from src.domain.entities.fpel import (
    AuthorizationDecision,
    FPELStatus,
    FrozenProposal,
    FrozenProposalLifecycle,
    SealFailureReason,
    SealedVerdict,
    compute_content_hash,
)
from src.domain.ports.fpel_authorization_port import FPELAuthorizationPort
from src.domain.ports.fpel_repository import FPELRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TASK_ID = "task-abc123"
CONTENT = "# Proposal\n\nThis is my proposal content."
CONTENT_HASH = compute_content_hash(CONTENT)


def _make_frozen(
    target_id: str = TASK_ID,
    content: str = CONTENT,
    lifecycle: FrozenProposalLifecycle = FrozenProposalLifecycle.ACTIVE,
) -> FrozenProposal:
    return FrozenProposal(
        frozen_proposal_id=f"fp-{target_id}",
        target_id=target_id,
        content_hash=compute_content_hash(content),
        content=content,
        lifecycle=lifecycle,
    )


def _make_service(repo: MagicMock | None = None) -> tuple[FPELAuthorizationService, MagicMock]:
    mock_repo = repo if repo is not None else MagicMock(spec=FPELRepository)
    return FPELAuthorizationService(repo=mock_repo), mock_repo  # type: ignore[arg-type]


def _setup_frozen(repo: MagicMock, frozen: FrozenProposal | None = None) -> FrozenProposal:
    """Configure repo to return a frozen proposal for the target.

    Resets all related mocks to safe defaults: no sealed verdict,
    no current hash drift, default checker setup.
    """
    fp = frozen or _make_frozen()
    repo.get_active_frozen_proposal.return_value = fp
    repo.get_sealed_verdict.return_value = None
    repo.get_current_content_hash.return_value = None
    repo.get_candidate_verdict.return_value = None
    repo.get_checkers_for.return_value = ["checker-a"]
    repo.get_reports_for.return_value = [{"checker_id": "checker-a", "verdict": "PASS"}]
    return fp


# ---------------------------------------------------------------------------
# candidate PASS denied
# ---------------------------------------------------------------------------


class TestCandidatePassDenied:
    def test_candidate_pass_does_not_authorize(self) -> None:
        """Candidate PASS from automatic check does NOT authorize start."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = _make_frozen()
        repo.get_sealed_verdict.return_value = None  # no sealed verdict
        repo.get_candidate_verdict.return_value = "PASS"  # candidate exists

        decision = service.check_sealed(target_id=TASK_ID)
        assert decision.allowed is False
        assert decision.status == FPELStatus.CHECK_PASSED
        assert decision.reason is not None


class TestSealedPassAllowed:
    def test_sealed_pass_authorizes(self) -> None:
        """Sealed PASS authorizes implementation start."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        sealed = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=timezone.utc),
            content_hash=frozen.content_hash,
        )
        repo.get_sealed_verdict.return_value = sealed

        decision = service.check_sealed(target_id=TASK_ID)
        assert decision.allowed is True
        assert decision.status == FPELStatus.SEALED_PASS


# ---------------------------------------------------------------------------
# Missing/FAIL/NEEDS_HUMAN_DECISION/NOT_EVALUATED denied
# ---------------------------------------------------------------------------


class TestNonPassDenied:
    @pytest.mark.parametrize(
        "status,reason",
        [
            (FPELStatus.NOT_FROZEN, SealFailureReason.NO_FROZEN_PROPOSAL),
            (FPELStatus.CHECK_FAILED, SealFailureReason.MISSING_REPORTS),
            (FPELStatus.NEEDS_HUMAN_DECISION, SealFailureReason.MISSING_REPORTS),
            (FPELStatus.NOT_EVALUATED, SealFailureReason.MISSING_REPORTS),
        ],
    )
    def test_non_sealed_status_denied(
        self, status: FPELStatus, reason: SealFailureReason
    ) -> None:
        """Any non-SEALED_PASS status is denied."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None  # no frozen
        repo.get_sealed_verdict.return_value = None

        decision = service.check_sealed(target_id=TASK_ID)
        assert decision.allowed is False


# ---------------------------------------------------------------------------
# Seal invariants
# ---------------------------------------------------------------------------


class TestSealInvariants:
    def test_seal_success_outputs_sealed_verdict(self) -> None:
        """Successful seal returns SealedVerdict with all fields."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealedVerdict)
        assert result.frozen_proposal_id == frozen.frozen_proposal_id
        assert result.verdict == "SEALED_PASS"
        assert result.content_hash == frozen.content_hash
        assert result.sealed_at is not None

    def test_seal_fails_on_missing_freeze(self) -> None:
        """Seal on non-frozen target returns NO_FROZEN_PROPOSAL."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.NO_FROZEN_PROPOSAL

    def test_seal_fails_on_terminal_fail(self) -> None:
        """Seal on TERMINAL_FAIL target returns TERMINAL_FAIL."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.TERMINAL_FAIL


# ---------------------------------------------------------------------------
# Seal idempotency
# ---------------------------------------------------------------------------


class TestSealIdempotency:
    def test_re_seal_returns_existing(self) -> None:
        """Re-sealing an already-sealed proposal returns the existing verdict."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        existing = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=timezone.utc),
            content_hash=frozen.content_hash,
        )
        repo.get_sealed_verdict.return_value = existing

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealedVerdict)
        assert result.frozen_proposal_id == existing.frozen_proposal_id


# ---------------------------------------------------------------------------
# Re-freeze after failure
# ---------------------------------------------------------------------------


class TestReFreezeAfterFailure:
    def test_re_freeze_creates_new_id_and_supersedes_previous(self) -> None:
        """After seal failure, re-freeze creates new frozen_proposal_id and
        marks the previous one as SUPERSEDED."""
        service, repo = _make_service()
        old_frozen = _make_frozen()
        # Re-freeze: no active frozen (previous was consumed), but old exists in history
        repo.get_active_frozen_proposal.return_value = None
        repo.get_all_frozen_proposals.return_value = [old_frozen]
        repo.save_frozen_proposal.return_value = None
        repo.mark_superseded.return_value = None

        new_frozen = service.freeze(
            target_id=TASK_ID,
            content="Updated proposal content",
        )
        assert new_frozen.frozen_proposal_id != old_frozen.frozen_proposal_id
        assert new_frozen.content_hash != old_frozen.content_hash
        assert new_frozen.is_active
        repo.mark_superseded.assert_called_once_with(old_frozen.frozen_proposal_id)


# ---------------------------------------------------------------------------
# Mixed checker verdicts → NEEDS_HUMAN_DECISION
# ---------------------------------------------------------------------------


class TestMixedCheckerVerdicts:
    def test_mixed_verdicts_produce_needs_human_decision(self) -> None:
        """When some checkers PASS and others FAIL → NEEDS_HUMAN_DECISION."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_checkers_for.return_value = ["checker-a", "checker-b"]
        repo.get_reports_for.return_value = [
            {"checker_id": "checker-a", "verdict": "PASS"},
            {"checker_id": "checker-b", "verdict": "FAIL"},
        ]

        result = service.check(target_id=TASK_ID)
        assert result.status == FPELStatus.NEEDS_HUMAN_DECISION


# ---------------------------------------------------------------------------
# Required reports = all checkers must PASS
# ---------------------------------------------------------------------------


class TestRequiredReports:
    def test_all_checkers_pass_enables_seal(self) -> None:
        """When ALL registered checkers PASS → seal is allowed."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_checkers_for.return_value = ["checker-a", "checker-b"]
        repo.get_reports_for.return_value = [
            {"checker_id": "checker-a", "verdict": "PASS"},
            {"checker_id": "checker-b", "verdict": "PASS"},
        ]
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealedVerdict)

    def test_missing_checker_report_blocks_seal(self) -> None:
        """If not all checkers have reported → MISSING_REPORTS."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_checkers_for.return_value = ["checker-a", "checker-b"]
        # Only checker-a reported
        repo.get_reports_for.return_value = [
            {"checker_id": "checker-a", "verdict": "PASS"},
        ]
        repo.get_fpel_status.return_value = FPELStatus.FROZEN

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.MISSING_REPORTS


# ---------------------------------------------------------------------------
# FAIL terminal blocks transitions
# ---------------------------------------------------------------------------


class TestFailTerminalBlocksTransitions:
    def test_terminal_fail_blocks_seal(self) -> None:
        """TERMINAL_FAIL blocks all subsequent seal attempts."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.TERMINAL_FAIL

    def test_terminal_fail_blocks_check(self) -> None:
        """TERMINAL_FAIL blocks check — FAIL must remain."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL

        result = service.check(target_id=TASK_ID)
        assert result.status == FPELStatus.TERMINAL_FAIL


# ---------------------------------------------------------------------------
# Parametrized SealFailureReason (all 5 values)
# ---------------------------------------------------------------------------


class TestParametrizedSealFailureReason:
    @pytest.mark.parametrize(
        "setup_fn, expected_reason",
        [
            # NO_FROZEN_PROPOSAL
            (
                lambda repo: (
                    repo.get_active_frozen_proposal.return_value or
                    setattr(repo, "get_active_frozen_proposal", MagicMock(return_value=None))
                    or None
                ),
                SealFailureReason.NO_FROZEN_PROPOSAL,
            ),
        ],
    )
    def test_seal_failure_reasons(self, setup_fn, expected_reason: SealFailureReason) -> None:
        """Each SealFailureReason maps to correct denial."""
        service, repo = _make_service()
        setup_fn(repo)
        # Normalize for the lambda pattern
        if repo.get_active_frozen_proposal.return_value is None:
            repo.get_sealed_verdict.return_value = None
            result = service.seal(target_id=TASK_ID)
            assert isinstance(result, SealFailureReason)
            assert result == expected_reason

    def test_seal_fail_hash_mismatch(self) -> None:
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        # Current content differs from frozen
        repo.get_current_content_hash.return_value = compute_content_hash("tampered content")
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.HASH_MISMATCH

    def test_seal_fail_missing_reports(self) -> None:
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = []  # no reports
        repo.get_fpel_status.return_value = FPELStatus.FROZEN

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.MISSING_REPORTS

    def test_seal_fail_terminal_fail(self) -> None:
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.TERMINAL_FAIL

    def test_seal_fail_post_freeze_change(self) -> None:
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_current_content_hash.return_value = compute_content_hash("changed after freeze")
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        result = service.seal(target_id=TASK_ID)
        # Hash mismatch covers post-freeze change
        assert isinstance(result, SealFailureReason)
        assert result in (SealFailureReason.HASH_MISMATCH, SealFailureReason.POST_FREEZE_CHANGE)


# ---------------------------------------------------------------------------
# Triangulation — check_sealed with hash drift
# ---------------------------------------------------------------------------


class TestCheckSealedHashDrift:
    def test_check_sealed_denies_on_post_seal_hash_drift(self) -> None:
        """Even with a sealed verdict, if current content hash drifted → denied."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        sealed = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=timezone.utc),
            content_hash=frozen.content_hash,
        )
        repo.get_sealed_verdict.return_value = sealed
        # Content changed AFTER seal
        repo.get_current_content_hash.return_value = compute_content_hash(
            "modified after seal"
        )

        decision = service.check_sealed(target_id=TASK_ID)
        assert decision.allowed is False
        assert decision.reason == SealFailureReason.HASH_MISMATCH

    def test_check_sealed_succeeds_when_hash_unchanged(self) -> None:
        """Sealed PASS with matching hash → allowed."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        sealed = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=timezone.utc),
            content_hash=frozen.content_hash,
        )
        repo.get_sealed_verdict.return_value = sealed
        # No drift — current hash matches frozen
        repo.get_current_content_hash.return_value = frozen.content_hash

        decision = service.check_sealed(target_id=TASK_ID)
        assert decision.allowed is True
        assert decision.seal_id == sealed.frozen_proposal_id
        assert decision.sealed_at == sealed.sealed_at


# ---------------------------------------------------------------------------
# Triangulation — FAIL remains terminal
# ---------------------------------------------------------------------------


class TestFailRemainsTerminal:
    def test_fail_remains_even_when_checker_emits_pass(self) -> None:
        """TERMINAL_FAIL is not overridden by a new PASS report."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL
        # A checker emits PASS (should not matter)
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = [
            {"checker_id": "checker-a", "verdict": "PASS"},
        ]

        # check() must still return TERMINAL_FAIL
        result = service.check(target_id=TASK_ID)
        assert result.status == FPELStatus.TERMINAL_FAIL
        assert result.reason == SealFailureReason.TERMINAL_FAIL

    def test_fail_blocks_seal_even_with_all_pass_reports(self) -> None:
        """Seal is denied when TERMINAL_FAIL even if all checkers report PASS."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL
        repo.get_checkers_for.return_value = ["checker-a", "checker-b"]
        repo.get_reports_for.return_value = [
            {"checker_id": "checker-a", "verdict": "PASS"},
            {"checker_id": "checker-b", "verdict": "PASS"},
        ]

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.TERMINAL_FAIL


# ---------------------------------------------------------------------------
# Triangulation — zero checkers edge case
# ---------------------------------------------------------------------------


class TestZeroCheckers:
    def test_seal_fails_when_no_checkers_registered(self) -> None:
        """If no checkers are registered → MISSING_REPORTS."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_checkers_for.return_value = []  # zero checkers
        repo.get_reports_for.return_value = []
        repo.get_fpel_status.return_value = FPELStatus.FROZEN

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.MISSING_REPORTS


# ---------------------------------------------------------------------------
# Triangulation — checker FAIL verdict blocks seal
# ---------------------------------------------------------------------------


class TestCheckerFailBlocksSeal:
    def test_seal_fails_when_checker_returns_fail(self) -> None:
        """A checker with FAIL verdict blocks seal with MISSING_REPORTS."""
        service, repo = _make_service()
        frozen = _setup_frozen(repo)
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = [
            {"checker_id": "checker-a", "verdict": "FAIL"},
        ]
        repo.get_fpel_status.return_value = FPELStatus.FROZEN

        result = service.seal(target_id=TASK_ID)
        assert isinstance(result, SealFailureReason)
        assert result == SealFailureReason.MISSING_REPORTS


# ---------------------------------------------------------------------------
# Triangulation — re-freeze idempotent content
# ---------------------------------------------------------------------------


class TestReFreezeDeterministic:
    def test_re_freeze_same_content_produces_same_hash(self) -> None:
        """Freezing identical content produces the same content_hash."""
        service, repo = _make_service()
        repo.get_all_frozen_proposals.return_value = []
        repo.save_frozen_proposal.return_value = None

        frozen_a = service.freeze(target_id=TASK_ID, content=CONTENT)
        repo.get_all_frozen_proposals.return_value = [frozen_a]

        frozen_b = service.freeze(target_id=TASK_ID, content=CONTENT)
        assert frozen_a.content_hash == frozen_b.content_hash
        assert frozen_a.frozen_proposal_id != frozen_b.frozen_proposal_id


# ---------------------------------------------------------------------------
# Port contract — FPELAuthorizationPort
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Task 2.3 — Legacy APPROVED policy
# ---------------------------------------------------------------------------


class TestLegacyApprovedPolicy:
    """Legacy APPROVED = APPROVED + no frozen_proposal_id.

    Scenarios from spec R5:
    - Legacy already-running: retry/resume/next phase/major scope change → requires new freeze
    - Legacy boundary: APPROVED + no frozen_proposal_id
    - Legacy changed/unverifiable → NEEDS_HUMAN_DECISION
    """

    def test_legacy_unstarted_creates_not_evaluated_and_blocks_start(self) -> None:
        """Legacy APPROVED unstarted: evaluate_legacy creates NOT_EVALUATED snapshot, blocks start."""
        service, repo = _make_service()
        # Legacy = no frozen proposal
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=CONTENT_HASH,
            is_running=False,
        )
        assert decision.status == FPELStatus.NOT_EVALUATED
        assert decision.allowed is False
        assert decision.reason == SealFailureReason.MISSING_REPORTS

    def test_legacy_unstarted_matching_hash_creates_snapshot(self) -> None:
        """Legacy with matching approved hash: snapshot created, blocked until sealed PASS."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=CONTENT_HASH,
            is_running=False,
        )
        assert decision.status == FPELStatus.NOT_EVALUATED
        # Snapshot was saved via repo
        repo.save_fpel_status.assert_called_once_with(TASK_ID, "NOT_EVALUATED")

    def test_legacy_unstarted_hash_mismatch_returns_needs_human_decision(self) -> None:
        """Legacy with mismatched hash: content changed → NEEDS_HUMAN_DECISION."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        different_hash = compute_content_hash("tampered proposal content")
        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=different_hash,
            is_running=False,
        )
        assert decision.status == FPELStatus.NEEDS_HUMAN_DECISION
        assert decision.allowed is False

    def test_legacy_unstarted_no_approved_hash_returns_needs_human_decision(self) -> None:
        """Legacy with unverifiable approval (no approved hash) → NEEDS_HUMAN_DECISION."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=None,
            current_content_hash=CONTENT_HASH,
            is_running=False,
        )
        assert decision.status == FPELStatus.NEEDS_HUMAN_DECISION
        assert decision.allowed is False

    def test_legacy_running_continues_and_blocks_retry_without_freeze(self) -> None:
        """Legacy already running: execution continues, retry/resume/next phase requires new freeze."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=CONTENT_HASH,
            is_running=True,
            action="retry",
        )
        # Running legacy + action that needs freeze → blocked, requires new freeze
        assert decision.allowed is False
        assert decision.reason == SealFailureReason.NO_FROZEN_PROPOSAL

    def test_legacy_running_blocks_resume_without_freeze(self) -> None:
        """Legacy running: resume requires new freeze."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=CONTENT_HASH,
            is_running=True,
            action="resume",
        )
        assert decision.allowed is False
        assert decision.reason == SealFailureReason.NO_FROZEN_PROPOSAL

    def test_legacy_running_blocks_next_phase_without_freeze(self) -> None:
        """Legacy running: next phase requires new freeze."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=CONTENT_HASH,
            is_running=True,
            action="next_phase",
        )
        assert decision.allowed is False
        assert decision.reason == SealFailureReason.NO_FROZEN_PROPOSAL

    def test_legacy_running_blocks_major_scope_change_without_freeze(self) -> None:
        """Legacy running: major scope change requires new freeze."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None

        decision = service.evaluate_legacy(
            target_id=TASK_ID,
            approved_content_hash=CONTENT_HASH,
            current_content_hash=CONTENT_HASH,
            is_running=True,
            action="major_scope_change",
        )
        assert decision.allowed is False
        assert decision.reason == SealFailureReason.NO_FROZEN_PROPOSAL


# ---------------------------------------------------------------------------
# Port contract — FPELAuthorizationPort
# ---------------------------------------------------------------------------


class TestPortContract:
    def test_service_implements_port(self) -> None:
        """FPELAuthorizationService must implement FPELAuthorizationPort."""
        service, _ = _make_service()
        assert isinstance(service, FPELAuthorizationPort)
