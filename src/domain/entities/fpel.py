"""FPEL domain entities — Frozen Proposal Evidence Loop.

Implements immutable domain types for FPEL authorization:
- FrozenProposal: immutable snapshot of a proposal/outline at freeze time
- FPELStatus: lifecycle status with TERMINAL_FAIL as sole terminal state
- SealFailureReason: reasons why sealing may be denied
- AuthorizationDecision: gate check result (allowed/denied + metadata)
- SealedVerdict: successful seal output
- Scope-change detection via canonical SHA-256 hash comparison
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SealFailureReason(StrEnum):
    """Reasons why a seal attempt may be denied."""

    HASH_MISMATCH = "HASH_MISMATCH"
    MISSING_REPORTS = "MISSING_REPORTS"
    TERMINAL_FAIL = "TERMINAL_FAIL"
    POST_FREEZE_CHANGE = "POST_FREEZE_CHANGE"
    NO_FROZEN_PROPOSAL = "NO_FROZEN_PROPOSAL"


class FPELStatus(StrEnum):
    """FPEL lifecycle status. TERMINAL_FAIL is the sole terminal state."""

    NOT_FROZEN = "NOT_FROZEN"
    FROZEN = "FROZEN"
    CHECK_PASSED = "CHECK_PASSED"
    CHECK_FAILED = "CHECK_FAILED"
    NEEDS_HUMAN_DECISION = "NEEDS_HUMAN_DECISION"
    SEALED_PASS = "SEALED_PASS"
    TERMINAL_FAIL = "TERMINAL_FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"

    @property
    def is_terminal(self) -> bool:
        """True only for TERMINAL_FAIL — the sole terminal FPELStatus."""
        return self == FPELStatus.TERMINAL_FAIL


class FrozenProposalLifecycle(StrEnum):
    """Lifecycle state of a FrozenProposal record (proposal-level, not FPELStatus)."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


# ---------------------------------------------------------------------------
# Canonical hashing
# ---------------------------------------------------------------------------


def _canonicalize(content: str) -> str:
    """Normalize content for deterministic hashing.

    Parses JSON and re-serializes with sorted keys and compact separators.
    Non-JSON content is returned as-is (already canonical at the string level).
    """
    try:
        parsed = json.loads(content)
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        return content


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 of canonically-serialized content."""
    canonical = _canonicalize(content)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_scope_change(frozen_hash: str, current_hash: str) -> bool:
    """Detect scope change by comparing content hashes.

    Returns True if hashes differ (scope change detected).
    """
    return frozen_hash != current_hash


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenProposal:
    """Immutable snapshot of a proposal/outline at freeze time.

    Attributes:
        frozen_proposal_id: Unique identifier for this frozen snapshot.
        target_id: The task or workflow this proposal belongs to.
        content_hash: SHA-256 hash of the proposal content at freeze time.
        content: The actual proposal content string.
        lifecycle: ACTIVE or SUPERSEDED (SUPERSEDED is terminal at proposal level).
    """

    frozen_proposal_id: str
    target_id: str
    content_hash: str
    content: str
    lifecycle: FrozenProposalLifecycle = FrozenProposalLifecycle.ACTIVE

    def __post_init__(self) -> None:
        if not isinstance(self.frozen_proposal_id, str) or not self.frozen_proposal_id:
            raise ValueError("frozen_proposal_id must be a non-empty string")
        if not isinstance(self.target_id, str) or not self.target_id:
            raise ValueError("target_id must be a non-empty string")
        if not isinstance(self.content_hash, str) or not self.content_hash:
            raise ValueError("content_hash must be a non-empty string")
        if self.content_hash != compute_content_hash(self.content):
            raise ValueError("content_hash must match canonical hash of content")

    @property
    def is_active(self) -> bool:
        """True if this proposal is ACTIVE (not SUPERSEDED)."""
        return self.lifecycle == FrozenProposalLifecycle.ACTIVE


@dataclass(frozen=True)
class SealedVerdict:
    """Successful seal output with frozen snapshot reference.

    Attributes:
        frozen_proposal_id: The frozen proposal this seal is bound to.
        verdict: Always "SEALED_PASS".
        sealed_at: Timestamp when sealing occurred.
        content_hash: Hash of the content at seal time.
    """

    frozen_proposal_id: str
    verdict: str
    sealed_at: datetime
    content_hash: str


@dataclass(frozen=True)
class AuthorizationDecision:
    """Result of FPEL authorization gate check.

    Attributes:
        allowed: Whether the action is authorized.
        status: Current FPEL status.
        frozen_proposal_id: ID of the frozen proposal (None if not frozen).
        content_hash: Hash of the content (None if not frozen).
        reason: SealFailureReason if denied, None if allowed.
        seal_id: ID of the seal if authorized.
        sealed_at: Timestamp of sealing if authorized.
    """

    allowed: bool
    status: FPELStatus
    frozen_proposal_id: str | None
    content_hash: str | None
    reason: SealFailureReason | None
    seal_id: str | None
    sealed_at: datetime | None
