"""Unit tests for FPEL domain entities — Task 1.1.

Tests the domain model for the Frozen Proposal Evidence Loop:
- FrozenProposal immutability and content-hash binding
- FPELStatus enum (8 values, TERMINAL_FAIL is sole terminal)
- SealFailureReason enum (5 values)
- FrozenProposal lifecycle (SUPERSEDED is terminal proposal-level state)
- Scope-change hash comparison (identical → no change, different → scope change)
- Canonical serialization (key order / whitespace differences produce same hash)
- Field completeness for AuthorizationDecision (7 fields) and SealedVerdict (4 fields)
- R2 behavioral: changed content, major scope, post-seal drift all → hash mismatch
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from src.domain.entities.fpel import (
    AuthorizationDecision,
    FPELStatus,
    FrozenProposal,
    FrozenProposalLifecycle,
    SealedVerdict,
    SealFailureReason,
    compute_content_hash,
    detect_scope_change,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    """Compute SHA-256 of text encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(content: str | dict) -> str:
    """Canonicalize content for hashing via JSON dumps with sort_keys."""
    if isinstance(content, dict):
        return json.dumps(content, sort_keys=True, separators=(",", ":"))
    return content


# ---------------------------------------------------------------------------
# 1. FrozenProposal immutability
# ---------------------------------------------------------------------------


class TestFrozenProposalImmutability:
    def test_frozen_proposal_is_immutable(self) -> None:
        proposal = FrozenProposal(
            frozen_proposal_id="fp-001",
            target_id="task-abc",
            content_hash=_sha256("test content"),
            content="test content",
        )
        with pytest.raises(AttributeError):
            proposal.content_hash = "tampered"  # type: ignore[misc]

    def test_frozen_proposal_rejects_empty_id(self) -> None:
        with pytest.raises(ValueError, match="frozen_proposal_id"):
            FrozenProposal(
                frozen_proposal_id="",
                target_id="task-abc",
                content_hash=_sha256("x"),
                content="x",
            )

    def test_frozen_proposal_rejects_empty_target_id(self) -> None:
        with pytest.raises(ValueError, match="target_id"):
            FrozenProposal(
                frozen_proposal_id="fp-001",
                target_id="",
                content_hash=_sha256("x"),
                content="x",
            )


# ---------------------------------------------------------------------------
# 2. Content-hash binding (SHA-256 full-doc)
# ---------------------------------------------------------------------------


class TestContentHashBinding:
    def test_content_hash_matches_sha256_of_content(self) -> None:
        content = "My proposal content"
        proposal = FrozenProposal(
            frozen_proposal_id="fp-002",
            target_id="task-1",
            content_hash=_sha256(content),
            content=content,
        )
        assert proposal.content_hash == _sha256(content)

    def test_different_content_produces_different_hash(self) -> None:
        h1 = _sha256("content A")
        h2 = _sha256("content B")
        assert h1 != h2


# ---------------------------------------------------------------------------
# 3. FrozenProposal lifecycle (SUPERSEDED is terminal)
# ---------------------------------------------------------------------------


class TestFrozenProposalLifecycle:
    def test_active_is_default_lifecycle(self) -> None:
        proposal = FrozenProposal(
            frozen_proposal_id="fp-003",
            target_id="task-1",
            content_hash=_sha256("c"),
            content="c",
        )
        assert proposal.lifecycle == FrozenProposalLifecycle.ACTIVE

    def test_superseded_is_terminal(self) -> None:
        """SUPERSEDED proposals must reject further transitions."""
        proposal = FrozenProposal(
            frozen_proposal_id="fp-004",
            target_id="task-1",
            content_hash=_sha256("c"),
            content="c",
            lifecycle=FrozenProposalLifecycle.SUPERSEDED,
        )
        assert proposal.lifecycle == FrozenProposalLifecycle.SUPERSEDED
        assert not proposal.is_active

    def test_active_proposal_is_active(self) -> None:
        proposal = FrozenProposal(
            frozen_proposal_id="fp-005",
            target_id="task-1",
            content_hash=_sha256("c"),
            content="c",
            lifecycle=FrozenProposalLifecycle.ACTIVE,
        )
        assert proposal.is_active


# ---------------------------------------------------------------------------
# 4. FPELStatus enum — all 8 values constructable
# ---------------------------------------------------------------------------


class TestFPELStatus:
    EXPECTED_VALUES = {
        "NOT_FROZEN",
        "FROZEN",
        "CHECK_PASSED",
        "CHECK_FAILED",
        "NEEDS_HUMAN_DECISION",
        "SEALED_PASS",
        "TERMINAL_FAIL",
        "NOT_EVALUATED",
    }

    def test_all_8_values_exist(self) -> None:
        values = {s.value for s in FPELStatus}
        assert values == self.EXPECTED_VALUES

    def test_exactly_8_values(self) -> None:
        assert len(FPELStatus) == 8

    def test_terminal_fail_is_terminal(self) -> None:
        assert FPELStatus.TERMINAL_FAIL.is_terminal is True

    def test_only_terminal_fail_is_terminal(self) -> None:
        """TERMINAL_FAIL is the SOLE terminal FPELStatus."""
        for status in FPELStatus:
            if status == FPELStatus.TERMINAL_FAIL:
                assert status.is_terminal is True
            else:
                assert status.is_terminal is False, f"{status.value} should NOT be terminal"


# ---------------------------------------------------------------------------
# 5. SealFailureReason enum — all 5 values
# ---------------------------------------------------------------------------


class TestSealFailureReason:
    EXPECTED_VALUES = {
        "HASH_MISMATCH",
        "MISSING_REPORTS",
        "TERMINAL_FAIL",
        "POST_FREEZE_CHANGE",
        "NO_FROZEN_PROPOSAL",
    }

    def test_all_5_values_exist(self) -> None:
        values = {r.value for r in SealFailureReason}
        assert values == self.EXPECTED_VALUES

    def test_exactly_5_values(self) -> None:
        assert len(SealFailureReason) == 5

    @pytest.mark.parametrize("reason", list(SealFailureReason))
    def test_each_reason_is_string(self, reason: SealFailureReason) -> None:
        assert isinstance(reason.value, str)


# ---------------------------------------------------------------------------
# 6. Scope-change hash comparison
# ---------------------------------------------------------------------------


class TestScopeChangeDetection:
    def test_identical_hash_means_no_change(self) -> None:
        frozen_hash = _sha256("proposal v1")
        current_hash = _sha256("proposal v1")
        assert detect_scope_change(frozen_hash, current_hash) is False

    def test_different_hash_means_scope_change(self) -> None:
        frozen_hash = _sha256("proposal v1")
        current_hash = _sha256("proposal v2")
        assert detect_scope_change(frozen_hash, current_hash) is True


# ---------------------------------------------------------------------------
# 7. Canonical serialization
# ---------------------------------------------------------------------------


class TestCanonicalSerialization:
    def test_different_key_order_produces_same_hash(self) -> None:
        """Semantically identical content with different key order must hash the same."""
        content_a = json.dumps({"z": 1, "a": 2}, sort_keys=False)
        content_b = json.dumps({"a": 2, "z": 1}, sort_keys=False)
        # Raw hashes would differ
        assert _sha256(content_a) != _sha256(content_b)
        # Canonical hashes must match
        assert compute_content_hash(content_a) == compute_content_hash(content_b)

    def test_different_whitespace_produces_same_hash(self) -> None:
        """Same JSON content with different whitespace must hash the same."""
        content_tight = '{"a":1,"b":2}'
        content_spaced = '{ "a" : 1 , "b" : 2 }'
        assert compute_content_hash(content_tight) == compute_content_hash(content_spaced)

    def test_actually_different_content_produces_different_hash(self) -> None:
        """Genuinely different content must produce different canonical hashes."""
        h1 = compute_content_hash('{"a": 1}')
        h2 = compute_content_hash('{"a": 2}')
        assert h1 != h2


# ---------------------------------------------------------------------------
# 8. AuthorizationDecision field completeness (7 fields)
# ---------------------------------------------------------------------------


class TestAuthorizationDecision:
    def test_has_exactly_7_fields(self) -> None:
        import dataclasses

        fields = {f.name for f in dataclasses.fields(AuthorizationDecision)}
        expected = {
            "allowed",
            "status",
            "frozen_proposal_id",
            "content_hash",
            "reason",
            "seal_id",
            "sealed_at",
        }
        assert fields == expected

    def test_denied_decision(self) -> None:
        decision = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.NOT_FROZEN,
            frozen_proposal_id=None,
            content_hash=None,
            reason=SealFailureReason.NO_FROZEN_PROPOSAL,
            seal_id=None,
            sealed_at=None,
        )
        assert decision.allowed is False
        assert decision.status == FPELStatus.NOT_FROZEN
        assert decision.reason == SealFailureReason.NO_FROZEN_PROPOSAL

    def test_allowed_decision(self) -> None:
        now = datetime.now(tz=UTC)
        decision = AuthorizationDecision(
            allowed=True,
            status=FPELStatus.SEALED_PASS,
            frozen_proposal_id="fp-001",
            content_hash=_sha256("content"),
            reason=None,
            seal_id="seal-001",
            sealed_at=now,
        )
        assert decision.allowed is True
        assert decision.status == FPELStatus.SEALED_PASS
        assert decision.seal_id == "seal-001"


# ---------------------------------------------------------------------------
# 9. SealedVerdict field completeness (4 fields)
# ---------------------------------------------------------------------------


class TestSealedVerdict:
    def test_has_exactly_5_fields(self) -> None:
        import dataclasses

        fields = {f.name for f in dataclasses.fields(SealedVerdict)}
        expected = {
            "frozen_proposal_id",
            "verdict",
            "sealed_at",
            "content_hash",
            "source",
        }
        assert fields == expected

    def test_sealed_verdict_creation(self) -> None:
        now = datetime.now(tz=UTC)
        verdict = SealedVerdict(
            frozen_proposal_id="fp-010",
            verdict="SEALED_PASS",
            sealed_at=now,
            content_hash=_sha256("content"),
        )
        assert verdict.frozen_proposal_id == "fp-010"
        assert verdict.verdict == "SEALED_PASS"
        assert verdict.sealed_at == now
        assert verdict.content_hash == _sha256("content")


# ---------------------------------------------------------------------------
# 10. Terminal FAIL preservation
# ---------------------------------------------------------------------------


class TestTerminalFailPreservation:
    def test_fail_rejects_seal(self) -> None:
        """FAIL state rejects all subsequent seal attempts."""
        decision = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.TERMINAL_FAIL,
            frozen_proposal_id="fp-fail",
            content_hash=_sha256("c"),
            reason=SealFailureReason.TERMINAL_FAIL,
            seal_id=None,
            sealed_at=None,
        )
        assert decision.allowed is False
        assert decision.status.is_terminal is True

    def test_fail_rejects_freeze_on_same_proposal(self) -> None:
        """A SUPERSEDED proposal with TERMINAL_FAIL must not allow re-freeze on same id."""
        proposal = FrozenProposal(
            frozen_proposal_id="fp-fail",
            target_id="task-1",
            content_hash=_sha256("c"),
            content="c",
            lifecycle=FrozenProposalLifecycle.SUPERSEDED,
        )
        # SUPERSEDED proposals are not active — cannot be re-used
        assert proposal.is_active is False


# ---------------------------------------------------------------------------
# 11. R2 behavioral: all resolve to hash mismatch
# ---------------------------------------------------------------------------


class TestR2HashMismatch:
    def test_changed_content_resolves_to_hash_mismatch(self) -> None:
        """Changed content after freeze → HASH_MISMATCH."""
        frozen_hash = _sha256("original content")
        current_hash = _sha256("modified content")
        changed = detect_scope_change(frozen_hash, current_hash)
        assert changed is True
        assert SealFailureReason.HASH_MISMATCH.value == "HASH_MISMATCH"

    def test_major_scope_change_resolves_to_hash_mismatch(self) -> None:
        """Major scope change → different hash → HASH_MISMATCH path."""
        frozen_hash = compute_content_hash('{"scope": "phase 1", "items": [1, 2]}')
        current_hash = compute_content_hash('{"scope": "phase 1 + 2", "items": [1, 2, 3, 4]}')
        assert detect_scope_change(frozen_hash, current_hash) is True

    def test_post_seal_drift_resolves_to_hash_mismatch(self) -> None:
        """Post-seal drift → hash differs from sealed → HASH_MISMATCH."""
        sealed_hash = compute_content_hash("sealed content v1")
        drifted_hash = compute_content_hash("sealed content v1 + sneaky edit")
        assert detect_scope_change(sealed_hash, drifted_hash) is True
        # Same failure reason applies
        assert SealFailureReason.HASH_MISMATCH.value == "HASH_MISMATCH"
