"""Unit tests for SqliteFPELRepository — Phase 1 RED.

Tests:
- check_sealed accepts current_hash parameter from caller
- get_reports_for includes report_content in returned dicts
"""

from pathlib import Path

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.fpel_repository import SqliteFPELRepository


def _create_repo(tmp_path: Path) -> tuple[DatabaseConnection, SqliteFPELRepository]:

    db_path = tmp_path / "test_fpel.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = Path(__file__).resolve().parents[5] / "src" / "infrastructure" / "persistence" / "migrations"
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
