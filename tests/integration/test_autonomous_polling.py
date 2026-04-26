"""Integration tests for autonomous agent polling.

Uses temp-file SQLite + temp directories for full-stack testing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.application.services.agent_polling_service import AgentPollingService, LaunchHandle
from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.orchestration_task import OrchestrationTaskStatus
from src.domain.entities.poll_run import PollRunStatus
from src.infrastructure.persistence.database import DatabaseConnection
from src.infrastructure.persistence.repositories.orchestration_task_repository import (
    SqliteOrchestrationTaskRepository,
)
from src.infrastructure.persistence.repositories.poll_run_repository import (
    SqlitePollRunRepository,
)
from src.infrastructure.polling.poll_run_directory import PollRunDirectory

_FAKE_HANDLE = LaunchHandle(method="subprocess", pid=99999, pgid=99999)


@pytest.fixture
def db(tmp_path: Path) -> DatabaseConnection:
    """Temp-file database with migrations applied."""
    from src.infrastructure.persistence.database import DatabaseConfig, JournalMode

    db_path = tmp_path / "test.db"
    conn = DatabaseConnection(DatabaseConfig(db_path=db_path, journal_mode=JournalMode.WAL))

    # Run migrations manually
    migrations_dir = Path("src/infrastructure/persistence/migrations")
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        sql = sql_file.read_text()
        with conn as c:
            c.executescript(sql)

    return conn


@pytest.fixture
def run_dir(tmp_path: Path) -> PollRunDirectory:
    return PollRunDirectory(base_dir=tmp_path / "poll-runs")


@pytest.fixture
def task_svc(db: DatabaseConnection) -> TaskBoardService:
    repo = SqliteOrchestrationTaskRepository(connection=db)
    return TaskBoardService(repo=repo)


@pytest.fixture
def svc(
    task_svc: TaskBoardService,
    db: DatabaseConnection,
    run_dir: PollRunDirectory,
) -> AgentPollingService:
    repo = SqlitePollRunRepository(connection=db)
    return AgentPollingService(
        task_service=task_svc,
        poll_run_repo=repo,
        run_dir=run_dir,
        max_concurrent=4,
    )


@pytest.fixture(autouse=True)
def _stub_spawn_agent():
    """Stub _spawn_agent to return a fake handle for all tests in this module.

    Tests focus on polling logic, not on actual tmux/subprocess agent spawning.
    """
    with patch.object(
        AgentPollingService,
        "_spawn_agent",
        return_value=_FAKE_HANDLE,
    ):
        yield


def _create_approved_task(task_svc: TaskBoardService, subject: str = "Test task") -> str:
    """Helper: create → submit → approve, return task_id."""
    task = task_svc.create(subject=subject)
    task_svc.submit_plan(task.id, plan_text="Auto plan")
    task_svc.approve(task.id, approved_by="test")
    return task.id


class TestFullPollingCycle:
    """End-to-end: create task → submit → approve → poll → verify."""

    def test_create_approve_poll_once(
        self, svc: AgentPollingService, task_svc: TaskBoardService
    ) -> None:
        task_id = _create_approved_task(task_svc, "Integration test task")

        # Poll once
        runs = svc.poll_once()
        assert len(runs) == 1
        assert runs[0].task_id == task_id
        assert runs[0].status == PollRunStatus.RUNNING

        # Verify task is now IN_PROGRESS
        updated_task = task_svc.get(task_id)
        assert updated_task is not None
        assert updated_task.status == OrchestrationTaskStatus.IN_PROGRESS

    def test_concurrency_cap(self, svc: AgentPollingService, task_svc: TaskBoardService) -> None:
        # Override cap
        svc._max_concurrent = 2  # noqa: SLF001

        # Create 3 approved tasks
        for i in range(3):
            _create_approved_task(task_svc, f"Task {i}")

        # Should only spawn 2 (cap is 2)
        runs = svc.poll_once()
        assert len(runs) == 2

        # After first poll, 2 tasks are now IN_PROGRESS, 1 is still APPROVED
        # But we have 2 active runs, so cap is full → returns 0
        runs = svc.poll_once()
        assert len(runs) == 0  # Cap full, 3rd task must wait

    def test_poll_picks_remaining_after_completion(
        self, svc: AgentPollingService, task_svc: TaskBoardService, run_dir: PollRunDirectory
    ) -> None:
        svc._max_concurrent = 1  # noqa: SLF001

        # Create 2 approved tasks
        tid1 = _create_approved_task(task_svc, "Task 1")
        tid2 = _create_approved_task(task_svc, "Task 2")

        # First poll spawns 1 (cap=1)
        runs = svc.poll_once()
        assert len(runs) == 1

        # Complete it
        status = run_dir.read_status(runs[0].id)
        assert status is not None
        status["status"] = "COMPLETED"
        run_dir.write_status(runs[0].id, status)
        svc.check_runs()

        # Now cap is free, second task should be picked up
        runs = svc.poll_once()
        assert len(runs) == 1
        assert runs[0].task_id in (tid1, tid2)  # picks one remaining

    def test_check_runs_completed(
        self, svc: AgentPollingService, task_svc: TaskBoardService, run_dir: PollRunDirectory
    ) -> None:
        # Setup: approve task and poll once
        task_id = _create_approved_task(task_svc, "Completion test")
        runs = svc.poll_once()
        assert len(runs) == 1
        run_id = runs[0].id

        # Simulate agent writing completion status
        status = run_dir.read_status(run_id)
        assert status is not None
        status["status"] = "COMPLETED"
        run_dir.write_status(run_id, status)

        # Check runs
        updated = svc.check_runs()
        assert len(updated) == 1
        assert updated[0].status == PollRunStatus.COMPLETED

        # Task should be completed too
        updated_task = task_svc.get(task_id)
        assert updated_task is not None
        assert updated_task.status == OrchestrationTaskStatus.COMPLETED

    def test_cancel_run(self, svc: AgentPollingService, task_svc: TaskBoardService) -> None:
        _create_approved_task(task_svc, "Cancel test")
        runs = svc.poll_once()
        run_id = runs[0].id

        # Cancel
        cancelled = svc.cancel_run(run_id)
        assert cancelled.status == PollRunStatus.CANCELLED

    def test_status_summary(self, svc: AgentPollingService, task_svc: TaskBoardService) -> None:
        _create_approved_task(task_svc, "Summary test")
        svc.poll_once()

        summary = svc.get_status_summary()
        assert summary.get("RUNNING", 0) == 1
        # count_by_status only returns statuses with runs
        assert "QUEUED" not in summary
