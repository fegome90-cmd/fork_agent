from __future__ import annotations

from pathlib import Path

import pytest

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
        try:
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
        finally:
            conn.close()

    def test_idempotent_returns_existing(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        try:
            content = "legacy content"
            target_id = "task-legacy-002"

            frozen1, sealed1 = service.snapshot_legacy(target_id=target_id, content=content)
            frozen2, sealed2 = service.snapshot_legacy(target_id=target_id, content=content)

            assert frozen1.frozen_proposal_id == frozen2.frozen_proposal_id
            assert sealed1.frozen_proposal_id == sealed2.frozen_proposal_id
            assert sealed1.source == "LEGACY_APPROVED"
        finally:
            conn.close()

    def test_raises_on_failed_proposal(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        try:
            content = "will fail"
            target_id = "task-legacy-003"

            service.freeze(target_id=target_id, content=content)
            service.mark_fail(target_id=target_id, reason="audit failed")

            with pytest.raises(ValueError, match="failed"):
                service.snapshot_legacy(target_id=target_id, content=content)
        finally:
            conn.close()

    def test_raises_on_active_unsealed_proposal(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        try:
            content = "unsealed content"
            target_id = "task-legacy-004"

            service.freeze(target_id=target_id, content=content)

            with pytest.raises(ValueError, match="active unsealed proposal"):
                service.snapshot_legacy(target_id=target_id, content=content)
        finally:
            conn.close()

    def test_idempotent_after_normal_snapshot(self, tmp_path: Path) -> None:
        service, repo, conn = _create_service(tmp_path)
        try:
            content = "verify no orphans"
            target_id = "task-legacy-005"

            frozen1, sealed1 = service.snapshot_legacy(target_id=target_id, content=content)

            all_proposals = repo.get_all_frozen_proposals(target_id)
            active = [p for p in all_proposals if p.is_active]
            assert len(active) == 1
            assert active[0].frozen_proposal_id == frozen1.frozen_proposal_id
        finally:
            conn.close()


class TestAtomicSupersedeAndSave:
    """Integration tests confirming no TOCTOU window in supersede+save."""

    def test_save_frozen_with_sealed_verdict_supersede_ids_atomic(self, tmp_path: Path) -> None:
        """After save with supersede_ids, old proposal is SUPERSEDED, new is ACTIVE."""
        service, repo, conn = _create_service(tmp_path)
        try:
            from datetime import UTC, datetime

            from src.domain.entities.fpel import FrozenProposal, SealedVerdict, compute_content_hash

            target_id = "task-atomic-001"
            content_old = "old content"
            content_new = "new content"

            # Seed an ACTIVE proposal
            old_proposal = FrozenProposal(
                frozen_proposal_id="fp-old-001",
                target_id=target_id,
                content_hash=compute_content_hash(content_old),
                content=content_old,
            )
            repo.save_frozen_proposal(old_proposal)

            # Create new proposal + sealed verdict with supersede
            new_proposal = FrozenProposal(
                frozen_proposal_id="fp-new-001",
                target_id=target_id,
                content_hash=compute_content_hash(content_new),
                content=content_new,
            )
            new_verdict = SealedVerdict(
                frozen_proposal_id="fp-new-001",
                verdict="SEALED_PASS",
                sealed_at=datetime.now(tz=UTC),
                content_hash=new_proposal.content_hash,
                source="LEGACY_APPROVED",
            )
            repo.save_frozen_with_sealed_verdict(
                new_proposal, new_verdict, supersede_ids=["fp-old-001"]
            )

            # Verify: old is SUPERSEDED, new is ACTIVE — single read
            all_proposals = repo.get_all_frozen_proposals(target_id)
            by_id = {p.frozen_proposal_id: p for p in all_proposals}
            assert by_id["fp-old-001"].lifecycle.value == "SUPERSEDED"
            assert by_id["fp-new-001"].lifecycle.value == "ACTIVE"

            # Only 1 active
            active = [p for p in all_proposals if p.is_active]
            assert len(active) == 1
            assert active[0].frozen_proposal_id == "fp-new-001"
        finally:
            conn.close()

    def test_freeze_uses_atomic_supersede(self, tmp_path: Path) -> None:
        """freeze() with existing active proposal uses atomic supersede path."""
        service, repo, conn = _create_service(tmp_path)
        try:
            target_id = "task-freeze-atomic"
            content_v1 = "version 1"
            content_v2 = "version 2"

            # First freeze
            frozen1 = service.freeze(target_id=target_id, content=content_v1)
            assert frozen1.content_hash == compute_content_hash(content_v1)

            # Second freeze — should atomically supersede first
            frozen2 = service.freeze(target_id=target_id, content=content_v2)
            assert frozen2.content_hash == compute_content_hash(content_v2)

            all_proposals = repo.get_all_frozen_proposals(target_id)
            active = [p for p in all_proposals if p.is_active]
            assert len(active) == 1
            assert active[0].frozen_proposal_id == frozen2.frozen_proposal_id
        finally:
            conn.close()
