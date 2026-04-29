"""Integration tests for FPEL runtime wiring — Phase 3.

Tests:
- Fail-closed: FPEL_ENABLED=1, no sealed PASS → TaskTransitionError
- Fail-open: FPEL_ENABLED unset → task transitions succeed without FPEL gate
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.application.exceptions import TaskTransitionError
from src.domain.entities.orchestration_task import OrchestrationTaskStatus
from src.infrastructure.persistence.container import get_task_board_service
from src.infrastructure.persistence.migrations import run_migrations


def _setup_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "fpel_integration.db"
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
    return db_path


class TestFailClosedDeniesWithoutSealedPass:
    """FPEL_ENABLED=1 + no sealed PASS → start() denied."""

    def test_fail_closed_denies_without_sealed_pass(self, tmp_path: Path) -> None:
        db_path = _setup_db(tmp_path)

        with patch.dict(os.environ, {"FPEL_ENABLED": "1"}):
            service = get_task_board_service(db_path=db_path)

            task = service.create(subject="FPEL integration test")
            task = service.submit_plan(task.id, plan_text="test plan")
            task = service.approve(task.id, approved_by="tester")

            with pytest.raises(TaskTransitionError):
                service.start(task.id, owner="agent")


class TestFailOpenWhenDisabled:
    """FPEL_ENABLED unset → task transitions succeed without FPEL gate."""

    def test_fail_open_when_disabled(self, tmp_path: Path) -> None:
        db_path = _setup_db(tmp_path)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FPEL_ENABLED", None)
            service = get_task_board_service(db_path=db_path)

            task = service.create(subject="FPEL disabled test")
            task = service.submit_plan(task.id, plan_text="test plan")
            task = service.approve(task.id, approved_by="tester")

            result = service.start(task.id, owner="agent")
            assert result.status == OrchestrationTaskStatus.IN_PROGRESS
