"""Unit tests for SqliteFPELRepository — Phase 1 RED.

Tests:
- check_sealed accepts current_hash parameter from caller
- get_reports_for includes report_content in returned dicts
- mark_failed() INSERT OR IGNORE idempotency (S5)
- is_failed() returns True/False correctly (S9)
- reason persistence round-trip (R6)
"""

from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import IntegrityError

import pytest

from src.domain.entities.fpel import FrozenProposal, SealedVerdict, compute_content_hash
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.fpel_repository import SqliteFPELRepository


def _create_repo(tmp_path: Path) -> tuple[DatabaseConnection, SqliteFPELRepository]:

    db_path = tmp_path / "test_fpel.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = (
        Path(__file__).resolve().parents[5]
        / "src"
        / "infrastructure"
        / "persistence"
        / "migrations"
    )
    run_migrations(config, migrations_dir)
    conn = DatabaseConnection(config=config)
    repo = SqliteFPELRepository(connection=conn)
    return conn, repo


class TestGetReportsForIncludesContent:
    """get_reports_for() MUST include report_content in returned dicts."""

    def test_get_reports_for_includes_content(self, tmp_path: Path) -> None:
        """Seed a report with content → returned dict has report_content key."""
        conn, repo = _create_repo(tmp_path)

        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-001", "target-1", "hash-abc", "proposal content"),
            )
            c.execute(
                "INSERT INTO fpel_checker_reports (frozen_proposal_id, checker_id, verdict, report_content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-001", "checker-a", "PASS", "detailed evidence here"),
            )
            c.commit()

        reports = repo.get_reports_for("fp-001")

        assert len(reports) == 1
        assert "report_content" in reports[0]
        assert reports[0]["report_content"] == "detailed evidence here"


class TestCheckSealedCurrentHash:
    """Verify that check_sealed accepts current_hash from caller."""

    def test_get_current_content_hash_uses_param(self) -> None:
        """When caller provides current_hash, check_sealed uses it directly.

        Tests at the service level: FPELAuthorizationService.check_sealed()
        accepts current_hash param and uses it for hash comparison.
        """
        from datetime import UTC, datetime
        from unittest.mock import MagicMock

        from src.application.services.fpel_authorization_service import (
            FPELAuthorizationService,
        )
        from src.domain.entities.fpel import (
            FrozenProposal,
            FrozenProposalLifecycle,
            SealedVerdict,
            compute_content_hash,
        )
        from src.domain.ports.fpel_repository import FPELRepository

        content = "proposal content for hash test"
        real_hash = compute_content_hash(content)
        repo = MagicMock(spec=FPELRepository)
        frozen = FrozenProposal(
            frozen_proposal_id="fp-001",
            target_id="target-1",
            content_hash=real_hash,
            content=content,
            lifecycle=FrozenProposalLifecycle.ACTIVE,
        )
        repo.get_active_frozen_proposal.return_value = frozen
        repo.is_failed.return_value = False
        repo.get_sealed_verdict.return_value = SealedVerdict(
            frozen_proposal_id="fp-001",
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash=real_hash,
        )
        repo.get_current_content_hash.return_value = real_hash

        service = FPELAuthorizationService(repo=repo)

        decision = service.check_sealed("target-1", current_hash=real_hash)

        assert decision.allowed is True
        repo.get_current_content_hash.assert_not_called()


# ---------------------------------------------------------------------------
# Task 1.1 — mark_failed + is_failed + reason round-trip (S5, S9, R6)
# ---------------------------------------------------------------------------


class TestMarkFailedIdempotency:
    """mark_failed() uses INSERT OR IGNORE — first-write-wins for reason."""

    def _seed_frozen(self, conn: DatabaseConnection, fp_id: str = "fp-fail-001") -> None:
        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                (fp_id, "target-fail", "hash-fail", "fail content"),
            )
            c.commit()

    def test_mark_failed_inserts_failure_row(self, tmp_path: Path) -> None:
        """mark_failed() creates a row in fpel_proposal_failures."""
        conn, repo = _create_repo(tmp_path)
        self._seed_frozen(conn)

        repo.mark_failed("fp-fail-001", reason="audit failure")

        assert repo.is_failed("fp-fail-001") is True

    def test_mark_failed_idempotent_second_call_no_error(self, tmp_path: Path) -> None:
        """Second mark_failed() is no-op — INSERT OR IGNORE (S5)."""
        conn, repo = _create_repo(tmp_path)
        self._seed_frozen(conn)

        repo.mark_failed("fp-fail-001", reason="first")
        repo.mark_failed("fp-fail-001", reason="second")

        assert repo.is_failed("fp-fail-001") is True

    def test_mark_failed_first_write_wins_reason(self, tmp_path: Path) -> None:
        """First reason preserved; subsequent calls with different reason ignored (S5)."""
        conn, repo = _create_repo(tmp_path)
        self._seed_frozen(conn)

        repo.mark_failed("fp-fail-001", reason="first reason")
        repo.mark_failed("fp-fail-001", reason="second reason")

        # Verify first reason is preserved via direct DB read
        with conn as c:
            row = c.execute(
                "SELECT reason FROM fpel_proposal_failures WHERE frozen_proposal_id = ?",
                ("fp-fail-001",),
            ).fetchone()
        assert row is not None
        assert row["reason"] == "first reason"

    def test_mark_failed_without_reason(self, tmp_path: Path) -> None:
        """mark_failed() with no reason stores NULL in reason column."""
        conn, repo = _create_repo(tmp_path)
        self._seed_frozen(conn)

        repo.mark_failed("fp-fail-001", reason=None)

        assert repo.is_failed("fp-fail-001") is True
        with conn as c:
            row = c.execute(
                "SELECT reason FROM fpel_proposal_failures WHERE frozen_proposal_id = ?",
                ("fp-fail-001",),
            ).fetchone()
        assert row is not None
        assert row["reason"] is None


class TestIsFailed:
    """is_failed() returns True when failed, False otherwise (S9)."""

    def test_is_failed_true_when_failure_row_exists(self, tmp_path: Path) -> None:
        """is_failed() returns True for a failed proposal."""
        conn, repo = _create_repo(tmp_path)
        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-failed", "target-x", "hash-x", "content-x"),
            )
            c.execute(
                "INSERT INTO fpel_proposal_failures (frozen_proposal_id, reason) VALUES (?, ?)",
                ("fp-failed", "some reason"),
            )
            c.commit()

        assert repo.is_failed("fp-failed") is True

    def test_is_failed_false_when_no_failure_row(self, tmp_path: Path) -> None:
        """is_failed() returns False for a non-failed proposal (S9)."""
        conn, repo = _create_repo(tmp_path)
        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-clean", "target-y", "hash-y", "content-y"),
            )
            c.commit()

        assert repo.is_failed("fp-clean") is False

    def test_is_failed_false_for_unknown_id(self, tmp_path: Path) -> None:
        """is_failed() returns False for a proposal that doesn't exist."""
        conn, repo = _create_repo(tmp_path)

        assert repo.is_failed("fp-nonexistent") is False


class TestReasonRoundTrip:
    """Reason persists correctly and is retrievable (R6)."""

    def test_reason_round_trip_via_direct_read(self, tmp_path: Path) -> None:
        """Reason stored via mark_failed() is readable from DB."""
        conn, repo = _create_repo(tmp_path)
        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-reason", "target-r", "hash-r", "content-r"),
            )
            c.commit()

        repo.mark_failed("fp-reason", reason="blocked by audit")

        with conn as c:
            row = c.execute(
                "SELECT reason FROM fpel_proposal_failures WHERE frozen_proposal_id = ?",
                ("fp-reason",),
            ).fetchone()
        assert row is not None
        assert row["reason"] == "blocked by audit"


class TestSealedVerdictSourceRoundTrip:
    def test_source_none_round_trip(self, tmp_path: Path) -> None:
        conn, repo = _create_repo(tmp_path)
        from datetime import UTC, datetime

        from src.domain.entities.fpel import SealedVerdict

        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-src-001", "target-src", "hash-src", "content-src"),
            )
            c.commit()

        sv = SealedVerdict(
            frozen_proposal_id="fp-src-001",
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash="hash-src",
            source=None,
        )
        repo.save_sealed_verdict(sv)

        result = repo.get_sealed_verdict("fp-src-001")
        assert result is not None
        assert result.source is None

    def test_source_legacy_approved_round_trip(self, tmp_path: Path) -> None:
        conn, repo = _create_repo(tmp_path)
        from datetime import UTC, datetime

        from src.domain.entities.fpel import SealedVerdict

        with conn as c:
            c.execute(
                "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
                "VALUES (?, ?, ?, ?)",
                ("fp-src-002", "target-src2", "hash-src2", "content-src2"),
            )
            c.commit()

        sv = SealedVerdict(
            frozen_proposal_id="fp-src-002",
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash="hash-src2",
            source="LEGACY_APPROVED",
        )
        repo.save_sealed_verdict(sv)

        result = repo.get_sealed_verdict("fp-src-002")
        assert result is not None
        assert result.source == "LEGACY_APPROVED"


class TestSaveFrozenWithSealedVerdictAtomic:
    def test_atomic_save_persists_both(self, tmp_path: Path) -> None:
        conn, repo = _create_repo(tmp_path)
        proposal = FrozenProposal(
            frozen_proposal_id="fp-atomic-001",
            target_id="target-atomic",
            content_hash=compute_content_hash("atomic content"),
            content="atomic content",
        )
        verdict = SealedVerdict(
            frozen_proposal_id="fp-atomic-001",
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash=proposal.content_hash,
            source="LEGACY_APPROVED",
        )
        repo.save_frozen_with_sealed_verdict(proposal, verdict)

        assert repo.get_active_frozen_proposal("target-atomic") is not None
        assert repo.get_sealed_verdict("fp-atomic-001") is not None

    def test_atomic_failure_leaves_no_partial_state(self, tmp_path: Path) -> None:
        conn, repo = _create_repo(tmp_path)
        proposal = FrozenProposal(
            frozen_proposal_id="fp-atomic-fail",
            target_id="target-fail",
            content_hash=compute_content_hash("will fail"),
            content="will fail",
        )
        bad_verdict = SealedVerdict(
            frozen_proposal_id="NONEXISTENT_FK",
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash="hash",
            source="LEGACY_APPROVED",
        )
        with pytest.raises(IntegrityError):
            repo.save_frozen_with_sealed_verdict(proposal, bad_verdict)

        assert repo.get_active_frozen_proposal("target-fail") is None
        assert repo.get_sealed_verdict("fp-atomic-fail") is None
