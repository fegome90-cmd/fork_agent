"""FPEL repository — SQLite adapter for FPEL data persistence.

Implements the FPELRepository protocol against SQLite with:
- Frozen proposal CRUD with lifecycle management
- Sealed verdict persistence with UNIQUE constraint enforcement
- Checker reports and candidate verdicts
- FPEL status tracking per target
"""

from __future__ import annotations

from datetime import datetime

from src.domain.entities.fpel import (
    FrozenProposal,
    FrozenProposalLifecycle,
    SealedVerdict,
)
from src.infrastructure.persistence.database import DatabaseConnection


class SqliteFPELRepository:
    """SQLite implementation of FPELRepository protocol."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def get_active_frozen_proposal(self, target_id: str) -> FrozenProposal | None:
        """Return the active (non-SUPERSEDED) frozen proposal for target."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT frozen_proposal_id, target_id, content_hash, content, lifecycle "
                "FROM frozen_proposals "
                "WHERE target_id = ? AND lifecycle = 'ACTIVE' "
                "ORDER BY created_at DESC LIMIT 1",
                (target_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return FrozenProposal(
            frozen_proposal_id=row["frozen_proposal_id"],
            target_id=row["target_id"],
            content_hash=row["content_hash"],
            content=row["content"],
            lifecycle=FrozenProposalLifecycle(row["lifecycle"]),
        )

    def get_all_frozen_proposals(self, target_id: str) -> list[FrozenProposal]:
        """Return all frozen proposals (including SUPERSEDED) for target."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT frozen_proposal_id, target_id, content_hash, content, lifecycle "
                "FROM frozen_proposals "
                "WHERE target_id = ? "
                "ORDER BY created_at DESC",
                (target_id,),
            )
            rows = cursor.fetchall()
        return [
            FrozenProposal(
                frozen_proposal_id=row["frozen_proposal_id"],
                target_id=row["target_id"],
                content_hash=row["content_hash"],
                content=row["content"],
                lifecycle=FrozenProposalLifecycle(row["lifecycle"]),
            )
            for row in rows
        ]

    def save_frozen_proposal(self, proposal: FrozenProposal) -> None:
        """Persist a new frozen proposal."""
        with self._connection as conn:
            conn.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content, lifecycle) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    proposal.frozen_proposal_id,
                    proposal.target_id,
                    proposal.content_hash,
                    proposal.content,
                    proposal.lifecycle.value,
                ),
            )

    def mark_superseded(self, frozen_proposal_id: str) -> None:
        """Mark a frozen proposal as SUPERSEDED (terminal at proposal level)."""
        with self._connection as conn:
            conn.execute(
                "UPDATE frozen_proposals SET lifecycle = 'SUPERSEDED' "
                "WHERE frozen_proposal_id = ?",
                (frozen_proposal_id,),
            )

    def get_sealed_verdict(self, frozen_proposal_id: str) -> SealedVerdict | None:
        """Return the sealed verdict for a frozen proposal, if any."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT frozen_proposal_id, verdict, sealed_at, content_hash "
                "FROM sealed_verdicts "
                "WHERE frozen_proposal_id = ?",
                (frozen_proposal_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return SealedVerdict(
            frozen_proposal_id=row["frozen_proposal_id"],
            verdict=row["verdict"],
            sealed_at=datetime.fromisoformat(row["sealed_at"]),
            content_hash=row["content_hash"],
        )

    def save_sealed_verdict(self, verdict: SealedVerdict) -> None:
        """Persist a sealed verdict."""
        with self._connection as conn:
            conn.execute(
                "INSERT INTO sealed_verdicts (frozen_proposal_id, verdict, sealed_at, content_hash) "
                "VALUES (?, ?, ?, ?)",
                (
                    verdict.frozen_proposal_id,
                    verdict.verdict,
                    verdict.sealed_at.isoformat(),
                    verdict.content_hash,
                ),
            )

    def get_checkers_for(self, target_id: str) -> list[str]:
        """Return registered checker IDs for target."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT DISTINCT checker_id FROM fpel_checker_reports cr "
                "JOIN frozen_proposals fp ON cr.frozen_proposal_id = fp.frozen_proposal_id "
                "WHERE fp.target_id = ? AND fp.lifecycle = 'ACTIVE'",
                (target_id,),
            )
            return [row["checker_id"] for row in cursor.fetchall()]

    def get_reports_for(self, frozen_proposal_id: str) -> list[dict]:
        """Return check reports for a frozen proposal."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT checker_id, verdict, report_content FROM fpel_checker_reports "
                "WHERE frozen_proposal_id = ?",
                (frozen_proposal_id,),
            )
            return [
                {"checker_id": row["checker_id"], "verdict": row["verdict"]}
                for row in cursor.fetchall()
            ]

    def get_candidate_verdict(self, frozen_proposal_id: str) -> str | None:
        """Return the candidate verdict (PASS/FAIL/etc.) if any."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT verdict FROM fpel_checker_reports "
                "WHERE frozen_proposal_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (frozen_proposal_id,),
            )
            row = cursor.fetchone()
        return row["verdict"] if row else None

    def get_current_content_hash(self, target_id: str) -> str | None:
        """Return the current content hash of the target's active proposal."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT content_hash FROM frozen_proposals "
                "WHERE target_id = ? AND lifecycle = 'ACTIVE' "
                "ORDER BY created_at DESC LIMIT 1",
                (target_id,),
            )
            row = cursor.fetchone()
        return row["content_hash"] if row else None

    def get_fpel_status(self, target_id: str) -> str | None:
        """Return the current FPEL status string for target."""
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT status FROM fpel_status WHERE target_id = ?",
                (target_id,),
            )
            row = cursor.fetchone()
        return row["status"] if row else None

    def save_fpel_status(self, target_id: str, status: str) -> None:
        """Update the FPEL status for target."""
        with self._connection as conn:
            conn.execute(
                "INSERT INTO fpel_status (target_id, status) VALUES (?, ?) "
                "ON CONFLICT(target_id) DO UPDATE SET status = excluded.status, "
                "updated_at = datetime('now')",
                (target_id, status),
            )
