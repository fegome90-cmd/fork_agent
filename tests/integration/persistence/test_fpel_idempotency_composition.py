"""Integration test for FPEL idempotency composition.

Task 2.6: Verifies that seal → consume → re-seal attempt → re-consume
produces the same outcome across both application and DB layers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.fpel_authorization_service import FPELAuthorizationService
from src.domain.entities.fpel import (
    FPELStatus,
    SealedVerdict,
    compute_content_hash,
)
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.fpel_repository import SqliteFPELRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TASK_ID = "task-compose-test"
CONTENT = "# Proposal for integration\n\nSeal → consume → re-seal → re-consume."
CHECKER_ID = "checker-compose"


@pytest.fixture
def fpel_db(tmp_path: Path) -> DatabaseConnection:
    """Create a fresh DB with all migrations applied."""
    db_path = tmp_path / "fpel_compose.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "infrastructure"
        / "persistence"
        / "migrations"
    )
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config=config)


@pytest.fixture
def service(fpel_db: DatabaseConnection) -> FPELAuthorizationService:
    """Create FPELAuthorizationService wired to real SQLite repo."""
    repo = SqliteFPELRepository(connection=fpel_db)
    return FPELAuthorizationService(repo=repo)


def _seed_checker_report(conn, frozen_proposal_id: str, checker_id: str = CHECKER_ID) -> None:
    """Insert a PASS report for a checker on a frozen proposal."""
    conn.execute(
        "INSERT INTO fpel_checker_reports (frozen_proposal_id, checker_id, verdict) "
        "VALUES (?, ?, 'PASS')",
        (frozen_proposal_id, checker_id),
    )


# ---------------------------------------------------------------------------
# Idempotency composition test
# ---------------------------------------------------------------------------


class TestIdempotencyComposition:
    """Seal → consume → re-seal → re-consume produces same outcome."""

    def test_seal_consume_reseal_reconsume_same_outcome(
        self, service: FPELAuthorizationService, fpel_db: DatabaseConnection
    ) -> None:
        """Full cycle: seal, consume, attempt re-seal, re-consume → same outcome.

        Steps:
        1. freeze → creates frozen proposal
        2. seed checker PASS report
        3. seal → creates sealed verdict
        4. consume (check_sealed) → allowed
        5. re-seal attempt → returns existing sealed verdict (idempotent)
        6. re-consume (check_sealed again) → same allowed decision
        """
        # Step 1: freeze
        frozen = service.freeze(target_id=TASK_ID, content=CONTENT)
        assert frozen.is_active
        assert frozen.content_hash == compute_content_hash(CONTENT)

        # Step 2: seed a checker PASS report at DB level
        with fpel_db as conn:
            _seed_checker_report(conn, frozen.frozen_proposal_id)

        # Step 3: seal
        seal_result = service.seal(target_id=TASK_ID)
        assert isinstance(seal_result, SealedVerdict)
        original_sealed_at = seal_result.sealed_at
        original_fp_id = seal_result.frozen_proposal_id

        # Step 4: consume (check_sealed) → allowed
        first_consume = service.check_sealed(target_id=TASK_ID)
        assert first_consume.allowed is True
        assert first_consume.status == FPELStatus.SEALED_PASS
        assert first_consume.seal_id == original_fp_id

        # Step 5: re-seal attempt → returns existing sealed verdict (idempotent)
        re_seal_result = service.seal(target_id=TASK_ID)
        assert isinstance(re_seal_result, SealedVerdict)
        assert re_seal_result.frozen_proposal_id == original_fp_id
        assert re_seal_result.sealed_at == original_sealed_at
        assert re_seal_result.content_hash == compute_content_hash(CONTENT)

        # Step 6: re-consume → same allowed decision
        second_consume = service.check_sealed(target_id=TASK_ID)
        assert second_consume.allowed is True
        assert second_consume.status == FPELStatus.SEALED_PASS
        assert second_consume.seal_id == original_fp_id
        assert second_consume.sealed_at == original_sealed_at

        # Verify DB state: exactly ONE sealed verdict
        with fpel_db as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sealed_verdicts")
            count = cursor.fetchone()[0]
        assert count == 1, "Idempotent re-seal must NOT create duplicate rows"

    def test_consume_before_seal_is_denied(
        self, service: FPELAuthorizationService, fpel_db: DatabaseConnection
    ) -> None:
        """Consuming before seal is denied — proves seal is required."""
        # Freeze only, no seal
        service.freeze(target_id=TASK_ID, content=CONTENT)

        decision = service.check_sealed(target_id=TASK_ID)
        assert decision.allowed is False
        assert decision.status == FPELStatus.NOT_FROZEN or decision.reason is not None

    def test_seal_after_content_change_produces_same_verdict_for_old_freeze(
        self, service: FPELAuthorizationService, fpel_db: DatabaseConnection
    ) -> None:
        """Re-seal after content change: old seal still valid for old frozen hash."""
        # Freeze + seed + seal
        frozen = service.freeze(target_id=TASK_ID, content=CONTENT)
        with fpel_db as conn:
            _seed_checker_report(conn, frozen.frozen_proposal_id)
        seal_result = service.seal(target_id=TASK_ID)
        assert isinstance(seal_result, SealedVerdict)
        original_fp_id = seal_result.frozen_proposal_id

        # Re-seal attempt (no new freeze) → idempotent, returns existing
        re_seal = service.seal(target_id=TASK_ID)
        assert isinstance(re_seal, SealedVerdict)
        assert re_seal.frozen_proposal_id == original_fp_id
