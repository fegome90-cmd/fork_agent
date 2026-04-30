from __future__ import annotations

from pathlib import Path

from src.application.services.fpel_authorization_service import FPELAuthorizationService
from src.domain.entities.fpel import FPELStatus, compute_content_hash
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.fpel_repository import SqliteFPELRepository


def _create_service(
    tmp_path: Path,
) -> tuple[FPELAuthorizationService, SqliteFPELRepository, DatabaseConnection]:
    db_path = tmp_path / "test_fpel_legacy.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "infrastructure"
        / "persistence"
        / "migrations"
    )
    run_migrations(config, migrations_dir)
    conn = DatabaseConnection(config=config)
    repo = SqliteFPELRepository(connection=conn)
    service = FPELAuthorizationService(repo=repo)
    return service, repo, conn


class TestLegacySnapshotRoundTrip:
    def test_full_roundtrip_freeze_seal_check(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        content = '{"task": "implement feature X"}'
        target_id = "task-legacy-001"

        frozen, sealed = service.snapshot_legacy(target_id=target_id, content=content)

        assert frozen.target_id == target_id
        assert frozen.content_hash == compute_content_hash(content)
        assert sealed.frozen_proposal_id == frozen.frozen_proposal_id
        assert sealed.verdict == "SEALED_PASS"
        assert sealed.source == "LEGACY_APPROVED"

        decision = service.check_sealed(target_id=target_id)
        assert decision.allowed is True
        assert decision.status == FPELStatus.SEALED_PASS

    def test_idempotent_returns_existing(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        content = "legacy content"
        target_id = "task-legacy-002"

        frozen1, sealed1 = service.snapshot_legacy(target_id=target_id, content=content)
        frozen2, sealed2 = service.snapshot_legacy(target_id=target_id, content=content)

        assert frozen1.frozen_proposal_id == frozen2.frozen_proposal_id
        assert sealed1.frozen_proposal_id == sealed2.frozen_proposal_id
        assert sealed1.source == "LEGACY_APPROVED"

    def test_raises_on_failed_proposal(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        content = "will fail"
        target_id = "task-legacy-003"

        service.freeze(target_id=target_id, content=content)
        service.mark_fail(target_id=target_id, reason="audit failed")

        import pytest

        with pytest.raises(ValueError, match="failed"):
            service.snapshot_legacy(target_id=target_id, content=content)
