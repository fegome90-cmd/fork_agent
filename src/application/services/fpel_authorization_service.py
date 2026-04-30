"""FPEL authorization service — implements FPELAuthorizationPort.

Orchestrates freeze/check/seal/status operations and scope-change detection
via SHA-256 content hash comparison with canonical serialization.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.domain.entities.fpel import (
    AuthorizationDecision,
    FPELStatus,
    FrozenProposal,
    SealedVerdict,
    SealFailureReason,
    compute_content_hash,
    detect_scope_change,
)
from src.domain.ports.fpel_repository import FPELRepository


class FPELAuthorizationService:
    """Application service implementing FPEL authorization gate.

    Checkers write evidence and verdict_candidate; only seal() creates
    final sealed PASS. Implements the FPELAuthorizationPort protocol.
    """

    __slots__ = ("_repo",)

    def __init__(self, repo: FPELRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # FPELAuthorizationPort.check_sealed
    # ------------------------------------------------------------------

    def check_sealed(
        self, target_id: str, current_hash: str | None = None
    ) -> AuthorizationDecision:
        """Check whether target has valid sealed PASS for current frozen hash.

        When current_hash is provided by the caller, uses it directly for
        post-seal drift comparison (avoids self-referential repository read).
        When None, falls back to repository query.
        """
        frozen = self._repo.get_active_frozen_proposal(target_id)
        if frozen is None:
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.NOT_FROZEN,
                frozen_proposal_id=None,
                content_hash=None,
                reason=SealFailureReason.NO_FROZEN_PROPOSAL,
                seal_id=None,
                sealed_at=None,
            )

        sealed = self._repo.get_sealed_verdict(frozen.frozen_proposal_id)
        if sealed is None:
            # No sealed verdict — check if candidate exists
            candidate = self._repo.get_candidate_verdict(frozen.frozen_proposal_id)
            status = FPELStatus.CHECK_PASSED if candidate == "PASS" else FPELStatus.FROZEN
            return AuthorizationDecision(
                allowed=False,
                status=status,
                frozen_proposal_id=frozen.frozen_proposal_id,
                content_hash=frozen.content_hash,
                reason=SealFailureReason.MISSING_REPORTS,
                seal_id=None,
                sealed_at=None,
            )

        # Sealed verdict exists — check for post-seal drift
        effective_hash = (
            current_hash
            if current_hash is not None
            else self._repo.get_current_content_hash(target_id)
        )
        if effective_hash is not None and detect_scope_change(sealed.content_hash, effective_hash):
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.SEALED_PASS,
                frozen_proposal_id=frozen.frozen_proposal_id,
                content_hash=current_hash,
                reason=SealFailureReason.HASH_MISMATCH,
                seal_id=None,
                sealed_at=None,
            )

        return AuthorizationDecision(
            allowed=True,
            status=FPELStatus.SEALED_PASS,
            frozen_proposal_id=frozen.frozen_proposal_id,
            content_hash=frozen.content_hash,
            reason=None,
            seal_id=sealed.frozen_proposal_id,
            sealed_at=sealed.sealed_at,
        )

    # ------------------------------------------------------------------
    # freeze
    # ------------------------------------------------------------------

    def freeze(self, target_id: str, content: str) -> FrozenProposal:
        """Create an immutable frozen snapshot of the proposal content.

        Any existing frozen proposals for this target are marked SUPERSEDED.
        """
        # Supersede all previous frozen proposals for this target
        existing = self._repo.get_all_frozen_proposals(target_id)
        for old_fp in existing:
            if old_fp.is_active:
                self._repo.mark_superseded(old_fp.frozen_proposal_id)

        content_hash = compute_content_hash(content)
        frozen_id = f"fp-{uuid.uuid4().hex[:12]}"

        proposal = FrozenProposal(
            frozen_proposal_id=frozen_id,
            target_id=target_id,
            content_hash=content_hash,
            content=content,
        )
        self._repo.save_frozen_proposal(proposal)
        return proposal

    def freeze_task(
        self, target_id: str, plan_text: str | None, subject: str, description: str | None = None
    ) -> FrozenProposal:
        """Freeze with canonical hash from an OrchestrationTask's content.

        Computes the same hash as ``compute_task_hash()`` so that
        ``check_sealed(current_hash=...)`` produces consistent results.
        """
        content = plan_text
        if content is None:
            parts = [subject]
            if description:
                parts.append(description)
            content = "\n".join(parts)
        return self.freeze(target_id, content)

    def freeze_plan(self, target_id: str, tasks: list[dict[str, str]]) -> FrozenProposal:
        """Freeze with canonical hash from a plan's task list.

        Computes the same hash as ``compute_plan_hash_from_tasks()`` so that
        ``check_sealed(current_hash=...)`` produces consistent results.

        Args:
            target_id: The plan session ID.
            tasks: List of dicts with id/slug/description keys.
        """
        import json

        task_data = [
            {"id": t["id"], "slug": t["slug"], "description": t["description"]} for t in tasks
        ]
        canonical = json.dumps(task_data, sort_keys=True, separators=(",", ":"))
        return self.freeze(target_id, canonical)

    # ------------------------------------------------------------------
    # check
    # ------------------------------------------------------------------

    def check(self, target_id: str) -> AuthorizationDecision:
        """Run checks and return the current FPEL status."""
        status_str = self._repo.get_fpel_status(target_id)

        if status_str == FPELStatus.TERMINAL_FAIL:
            frozen = self._repo.get_active_frozen_proposal(target_id)
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.TERMINAL_FAIL,
                frozen_proposal_id=frozen.frozen_proposal_id if frozen else None,
                content_hash=frozen.content_hash if frozen else None,
                reason=SealFailureReason.TERMINAL_FAIL,
                seal_id=None,
                sealed_at=None,
            )

        # Evaluate checker reports
        frozen = self._repo.get_active_frozen_proposal(target_id)
        if frozen is None:
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.NOT_FROZEN,
                frozen_proposal_id=None,
                content_hash=None,
                reason=SealFailureReason.NO_FROZEN_PROPOSAL,
                seal_id=None,
                sealed_at=None,
            )

        checkers = self._repo.get_checkers_for(target_id)
        reports = self._repo.get_reports_for(frozen.frozen_proposal_id)

        if not checkers:
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.FROZEN,
                frozen_proposal_id=frozen.frozen_proposal_id,
                content_hash=frozen.content_hash,
                reason=SealFailureReason.MISSING_REPORTS,
                seal_id=None,
                sealed_at=None,
            )

        report_by_checker = {r["checker_id"]: r["verdict"] for r in reports}
        all_pass = all(report_by_checker.get(c) == "PASS" for c in checkers)
        any_fail = any(report_by_checker.get(c) == "FAIL" for c in checkers)

        if any_fail:
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.NEEDS_HUMAN_DECISION,
                frozen_proposal_id=frozen.frozen_proposal_id,
                content_hash=frozen.content_hash,
                reason=SealFailureReason.MISSING_REPORTS,
                seal_id=None,
                sealed_at=None,
            )

        if all_pass:
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.CHECK_PASSED,
                frozen_proposal_id=frozen.frozen_proposal_id,
                content_hash=frozen.content_hash,
                reason=None,
                seal_id=None,
                sealed_at=None,
            )

        return AuthorizationDecision(
            allowed=False,
            status=FPELStatus.FROZEN,
            frozen_proposal_id=frozen.frozen_proposal_id,
            content_hash=frozen.content_hash,
            reason=SealFailureReason.MISSING_REPORTS,
            seal_id=None,
            sealed_at=None,
        )

    # ------------------------------------------------------------------
    # seal
    # ------------------------------------------------------------------

    def seal(self, target_id: str) -> SealedVerdict | SealFailureReason:
        """Validate invariants and create sealed PASS, or return failure reason."""
        frozen = self._repo.get_active_frozen_proposal(target_id)
        if frozen is None:
            return SealFailureReason.NO_FROZEN_PROPOSAL

        # Check for existing sealed verdict (idempotency)
        existing = self._repo.get_sealed_verdict(frozen.frozen_proposal_id)
        if existing is not None:
            return existing

        # Check terminal FAIL
        status_str = self._repo.get_fpel_status(target_id)
        if status_str == FPELStatus.TERMINAL_FAIL:
            return SealFailureReason.TERMINAL_FAIL

        # Check hash integrity
        current_hash = self._repo.get_current_content_hash(target_id)
        if current_hash is not None and detect_scope_change(frozen.content_hash, current_hash):
            return SealFailureReason.HASH_MISMATCH

        # Check all registered checkers have PASS
        checkers = self._repo.get_checkers_for(target_id)
        reports = self._repo.get_reports_for(frozen.frozen_proposal_id)
        report_by_checker = {r["checker_id"]: r["verdict"] for r in reports}

        if len(checkers) == 0:
            return SealFailureReason.MISSING_REPORTS

        for checker_id in checkers:
            verdict = report_by_checker.get(checker_id)
            if verdict != "PASS":
                return SealFailureReason.MISSING_REPORTS

        # All checks pass — create sealed verdict
        sealed = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash=frozen.content_hash,
        )
        self._repo.save_sealed_verdict(sealed)
        return sealed

    # ------------------------------------------------------------------
    # Legacy APPROVED policy
    # ------------------------------------------------------------------

    def evaluate_legacy(
        self,
        target_id: str,
        approved_content_hash: str | None,
        current_content_hash: str | None,
        is_running: bool = False,
        action: str | None = None,
    ) -> AuthorizationDecision:
        """Evaluate legacy APPROVED task (APPROVED + no frozen_proposal_id).

        Per spec R5:
        - Unstarted + matching hash → NOT_EVALUATED snapshot, blocked until sealed PASS
        - Unstarted + mismatched hash → NEEDS_HUMAN_DECISION
        - Unstarted + no approved hash (unverifiable) → NEEDS_HUMAN_DECISION
        - Running + retry/resume/next_phase/major_scope_change → NO_FROZEN_PROPOSAL (needs new freeze)
        """
        _ACTIONS_REQUIRING_FREEZE = frozenset(
            {
                "retry",
                "resume",
                "next_phase",
                "major_scope_change",
            }
        )

        # Already-running legacy with an action that requires freeze
        if is_running and action in _ACTIONS_REQUIRING_FREEZE:
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.NOT_FROZEN,
                frozen_proposal_id=None,
                content_hash=current_content_hash,
                reason=SealFailureReason.NO_FROZEN_PROPOSAL,
                seal_id=None,
                sealed_at=None,
            )

        # Unstarted legacy — check hash verifiability
        if approved_content_hash is None:
            # Unverifiable — no original approved hash to compare
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.NEEDS_HUMAN_DECISION,
                frozen_proposal_id=None,
                content_hash=current_content_hash,
                reason=SealFailureReason.MISSING_REPORTS,
                seal_id=None,
                sealed_at=None,
            )

        # Check if current content matches approved
        if current_content_hash != approved_content_hash:
            # Content changed since approval → NEEDS_HUMAN_DECISION
            return AuthorizationDecision(
                allowed=False,
                status=FPELStatus.NEEDS_HUMAN_DECISION,
                frozen_proposal_id=None,
                content_hash=current_content_hash,
                reason=SealFailureReason.MISSING_REPORTS,
                seal_id=None,
                sealed_at=None,
            )

        # Matching hash — create NOT_EVALUATED snapshot, block until sealed PASS
        self._repo.save_fpel_status(target_id, FPELStatus.NOT_EVALUATED)
        return AuthorizationDecision(
            allowed=False,
            status=FPELStatus.NOT_EVALUATED,
            frozen_proposal_id=None,
            content_hash=current_content_hash,
            reason=SealFailureReason.MISSING_REPORTS,
            seal_id=None,
            sealed_at=None,
        )
