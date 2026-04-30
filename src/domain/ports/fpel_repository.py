"""FPEL repository port — interface for FPEL data persistence.

Infrastructure layer implements this protocol against SQLite.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.entities.fpel import FrozenProposal, SealedVerdict


@runtime_checkable
class FPELRepository(Protocol):
    """Repository interface for FPEL snapshots, reports, candidates, and sealed verdicts."""

    def get_active_frozen_proposal(self, target_id: str) -> FrozenProposal | None:
        """Return the active (non-SUPERSEDED) frozen proposal for target."""
        ...

    def get_all_frozen_proposals(self, target_id: str) -> list[FrozenProposal]:
        """Return all frozen proposals (including SUPERSEDED) for target."""
        ...

    def save_frozen_proposal(self, proposal: FrozenProposal) -> None:
        """Persist a new frozen proposal."""
        ...

    def mark_superseded(self, frozen_proposal_id: str) -> None:
        """Mark a frozen proposal as SUPERSEDED (terminal at proposal level)."""
        ...

    def get_sealed_verdict(self, frozen_proposal_id: str) -> SealedVerdict | None:
        """Return the sealed verdict for a frozen proposal, if any."""
        ...

    def save_sealed_verdict(self, verdict: SealedVerdict) -> None:
        """Persist a sealed verdict."""
        ...

    def get_checkers_for(self, target_id: str) -> list[str]:
        """Return registered checker IDs for target."""
        ...

    def get_reports_for(self, frozen_proposal_id: str) -> list[dict]:
        """Return check reports for a frozen proposal."""
        ...

    def get_candidate_verdict(self, frozen_proposal_id: str) -> str | None:
        """Return the candidate verdict (PASS/FAIL/etc.) if any."""
        ...

    def get_current_content_hash(self, target_id: str) -> str | None:
        """Return the current content hash of the target's proposal."""
        ...

    def get_fpel_status(self, target_id: str) -> str | None:
        """Return the current FPEL status string for target."""
        ...

    def save_fpel_status(self, target_id: str, status: str) -> None:
        """Update the FPEL status for target."""
        ...

    def mark_failed(self, frozen_proposal_id: str, reason: str | None = None) -> None:
        """INSERT OR IGNORE — idempotent terminal FAIL marker.

        First-write-wins for reason: subsequent calls with different reason are silently ignored.
        """
        ...

    def is_failed(self, frozen_proposal_id: str) -> bool:
        """Single PK lookup — returns True if proposal has FAIL marker."""
        ...

    def save_frozen_with_sealed_verdict(
        self, proposal: FrozenProposal, verdict: SealedVerdict
    ) -> None:
        """Atomic: persist frozen proposal + sealed verdict in one transaction."""
        ...
