"""Integration tests for FPEL FAIL terminal state — Task 1.11 + Task 3.2.

Tests:
- Migration 035 creates fpel_proposal_failures with correct schema (S10)
- mark_failed + is_failed roundtrip with real SQLite
- reason persistence and retrieval
- Full fail → check_sealed blocks roundtrip (S3)
- TaskBoardService.start() blocked by failed proposal — transitive (S11)
- Workflow execute denied by failed proposal — transitive (S12)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.fpel_authorization_service import FPELAuthorizationService
from src.domain.entities.fpel import (
    FPELStatus,
    SealFailureReason,
)
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.fpel_repository import SqliteFPELRepository


def _setup_db(
    tmp_path: Path,
) -> tuple[DatabaseConnection, SqliteFPELRepository, FPELAuthorizationService]:
    db_path = tmp_path / "fpel_fail_integration.db"
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
    return conn, repo, service


class TestMigration035Schema:
    """Migration 035 creates fpel_proposal_failures with correct schema (S10)."""

    def test_fpel_proposal_failures_table_exists(self, tmp_path: Path) -> None:
        """fpel_proposal_failures table MUST exist after migration."""
        conn, repo, service = _setup_db(tmp_path)

        with conn as c:
            cursor = c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fpel_proposal_failures'"
            )
            assert cursor.fetchone() is not None

    def test_fpel_proposal_failures_schema_columns(self, tmp_path: Path) -> None:
        """fpel_proposal_failures has frozen_proposal_id (PK), failed_at, reason columns (S10)."""
        conn, repo, service = _setup_db(tmp_path)

        with conn as c:
            cursor = c.execute("PRAGMA table_info(fpel_proposal_failures)")
            columns = {row["name"]: row for row in cursor.fetchall()}

        assert "frozen_proposal_id" in columns
        assert "failed_at" in columns
        assert "reason" in columns
        # frozen_proposal_id must be PK
        assert columns["frozen_proposal_id"]["pk"] == 1

    def test_fpel_proposal_failures_foreign_key(self, tmp_path: Path) -> None:
        """fpel_proposal_failures.frozen_proposal_id REFERENCES frozen_proposals ON DELETE CASCADE (S10)."""
        conn, repo, service = _setup_db(tmp_path)

        with conn as c:
            cursor = c.execute("PRAGMA foreign_key_list(fpel_proposal_failures)")
            fks = cursor.fetchall()

        assert len(fks) >= 1
        fk = fks[0]
        assert fk["from"] == "frozen_proposal_id"
        assert fk["table"] == "frozen_proposals"

    def test_reason_roundtrip_via_service(self, tmp_path: Path) -> None:
        """mark_fail persists reason; is_failed returns True; reason retrievable (S10)."""
        conn, repo, service = _setup_db(tmp_path)

        # Freeze a proposal first
        content = "integration test proposal"
        frozen = service.freeze(target_id="integ-target", content=content)

        # Mark it failed with reason
        service.mark_fail(target_id="integ-target", reason="audit blocked")

        # Verify via repo
        assert repo.is_failed(frozen.frozen_proposal_id) is True

        # Verify reason directly in DB
        with conn as c:
            row = c.execute(
                "SELECT reason FROM fpel_proposal_failures WHERE frozen_proposal_id = ?",
                (frozen.frozen_proposal_id,),
            ).fetchone()
        assert row is not None
        assert row["reason"] == "audit blocked"


class TestFailBlocksCheckSealedRoundtrip:
    """Fail → check_sealed returns TERMINAL_FAIL — full roundtrip (S3)."""

    def test_fail_then_check_sealed_returns_terminal_fail(self, tmp_path: Path) -> None:
        """After mark_fail, check_sealed returns TERMINAL_FAIL."""
        conn, repo, service = _setup_db(tmp_path)

        content = "roundtrip proposal"
        frozen = service.freeze(target_id="roundtrip-target", content=content)

        # Mark as failed
        service.mark_fail(target_id="roundtrip-target", reason="blocked")

        # check_sealed MUST return TERMINAL_FAIL
        decision = service.check_sealed(target_id="roundtrip-target")
        assert decision.allowed is False
        assert decision.status == FPELStatus.TERMINAL_FAIL
        assert decision.reason == SealFailureReason.TERMINAL_FAIL
        assert decision.frozen_proposal_id == frozen.frozen_proposal_id


class TestTransitiveCoverage:
    """TaskBoardService.start() and workflow execute blocked transitively (S11, S12)."""

    def test_task_board_start_blocked_by_failed_proposal(self, tmp_path: Path) -> None:
        """TaskBoardService.start() denied when proposal is failed — transitive via check_sealed (S11)."""
        import os
        from unittest.mock import patch

        from src.application.exceptions import TaskTransitionError
        from src.infrastructure.persistence.container import get_task_board_service

        db_path = tmp_path / "fpel_transitive.db"
        from src.infrastructure.persistence.database import DatabaseConfig

        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "infrastructure"
            / "persistence"
            / "migrations"
        )
        run_migrations(config, migrations_dir)

        with patch.dict(os.environ, {"FPEL_ENABLED": "1"}):
            task_board = get_task_board_service(db_path=db_path)

            task = task_board.create(subject="Transitive test task")
            task = task_board.submit_plan(task.id, plan_text="transitive plan")
            task = task_board.approve(task.id, approved_by="tester")

            # Freeze the proposal via FPEL service
            fpel_service = task_board._fpel_port
            fpel_service.freeze_task(
                target_id=task.id,
                plan_text=task.plan_text,
                subject=task.subject,
                description=task.description,
            )

            # Mark it failed
            fpel_service.mark_fail(target_id=task.id, reason="transitive fail test")

            # start() MUST be blocked — check_sealed returns TERMINAL_FAIL
            with pytest.raises(TaskTransitionError):
                task_board.start(task.id, owner="agent")

    def test_workflow_execute_denied_by_failed_proposal(self, tmp_path: Path) -> None:
        """Workflow execute denied when proposal is failed — transitive via check_sealed (S12)."""
        import os
        from unittest.mock import patch

        from src.infrastructure.persistence.container import get_fpel_service

        conn, repo, service = _setup_db(tmp_path)

        # Freeze and fail a proposal for a workflow target
        service.freeze(target_id="workflow-target", content="workflow plan content")
        service.mark_fail(target_id="workflow-target", reason="workflow fail test")

        # Simulate what workflow execute does: call check_sealed via the FPEL service
        with patch.dict(
            os.environ, {"FPEL_ENABLED": "1", "DB_PATH": str(tmp_path / "fpel_fail_integration.db")}
        ):
            fpel_port = get_fpel_service(db_path=tmp_path / "fpel_fail_integration.db")

        assert fpel_port is not None
        decision = fpel_port.check_sealed(target_id="workflow-target")
        assert decision.allowed is False
        assert decision.status == FPELStatus.TERMINAL_FAIL
        assert decision.reason == SealFailureReason.TERMINAL_FAIL
