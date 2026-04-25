"""Polling + lifecycle integration tests.

Wires real AgentLaunchLifecycleService (in-memory SQLite) into
AgentPollingService to verify suppress / quarantine / confirm paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.agent_launch_lifecycle_service import (
    AgentLaunchLifecycleService,
)
from src.application.services.agent_polling_service import AgentPollingService
from src.domain.entities.poll_run import PollRunStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.agent_launch_repository import (
    SqliteAgentLaunchRepository,
)
from src.infrastructure.persistence.repositories.poll_run_repository import (
    SqlitePollRunRepository,
)


@pytest.fixture
def in_memory_db(tmp_path: Path) -> DatabaseConnection:
    """Create an in-memory SQLite with migrations applied."""
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    # Resolve migrations dir from project root
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    migrations_dir = project_root / "src" / "infrastructure" / "persistence" / "migrations"
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config=config)


@pytest.fixture
def lifecycle_svc(in_memory_db: DatabaseConnection) -> AgentLaunchLifecycleService:
    repo = SqliteAgentLaunchRepository(connection=in_memory_db)
    return AgentLaunchLifecycleService(registry=repo, lease_duration_ms=300_000)


@pytest.fixture
def poll_run_repo(in_memory_db: DatabaseConnection) -> SqlitePollRunRepository:
    return SqlitePollRunRepository(connection=in_memory_db)


def _make_polling_service(
    lifecycle_svc: AgentLaunchLifecycleService,
    poll_run_repo: SqlitePollRunRepository,
    run_dir: MagicMock,
) -> AgentPollingService:
    task_svc = MagicMock()
    task_svc.list.return_value = []
    return AgentPollingService(
        task_service=task_svc,
        poll_run_repo=poll_run_repo,
        run_dir=run_dir,
        lifecycle_service=lifecycle_svc,
    )


class TestPollOnceSuppressesWhenLifecycleBlocks:
    def test_suppresses_blocked_task(self, lifecycle_svc, poll_run_repo, tmp_path):
        """poll_once should not launch when lifecycle already has an active launch."""
        # Pre-claim a launch for this task
        attempt = lifecycle_svc.request_launch("task:task-1", "polling", "task", "task-1")
        assert attempt.decision == "claimed"

        # Seed an approved task
        task_svc = MagicMock()
        task = MagicMock()
        task.id = "task-1"
        task.subject = "test task"
        task_svc.list.return_value = [task]

        run_dir = MagicMock()
        run_dir_mock = tmp_path / "runs"
        run_dir_mock.mkdir()
        run_dir.create_run_dir.return_value = run_dir_mock

        svc = AgentPollingService(
            task_service=task_svc,
            poll_run_repo=poll_run_repo,
            run_dir=run_dir,
            lifecycle_service=lifecycle_svc,
        )

        runs = svc.poll_once()
        # No new runs because task-1 is already blocked by the pre-claimed launch
        assert len(runs) == 0


class TestSpawnRunQuarantinesWhenLifecycleDenies:
    def test_quarantines_on_suppressed(self, lifecycle_svc, poll_run_repo, tmp_path):
        """_spawn_run should quarantine when lifecycle denies the launch."""
        # Pre-claim to suppress
        lifecycle_svc.request_launch("task:task-2", "polling", "task", "task-2")

        run_dir = MagicMock()
        run_dir_mock = tmp_path / "runs"
        run_dir_mock.mkdir()
        run_dir.create_run_dir.return_value = run_dir_mock

        task_svc = MagicMock()
        svc = AgentPollingService(
            task_service=task_svc,
            poll_run_repo=poll_run_repo,
            run_dir=run_dir,
            lifecycle_service=lifecycle_svc,
        )

        run = svc._spawn_run("task-2", "test")
        assert run.status == PollRunStatus.CANCELLED
        assert "suppressed" in (run.error_message or "").lower()


class TestSpawnRunConfirmsActiveAfterSpawn:
    def test_confirms_active(self, lifecycle_svc, poll_run_repo, tmp_path):
        """_spawn_run should call confirm_active after successful spawn."""
        run_dir = MagicMock()
        run_dir_mock = tmp_path / "runs"
        run_dir_mock.mkdir()
        run_dir.create_run_dir.return_value = run_dir_mock

        task_svc = MagicMock()

        svc = AgentPollingService(
            task_service=task_svc,
            poll_run_repo=poll_run_repo,
            run_dir=run_dir,
            lifecycle_service=lifecycle_svc,
        )

        # Mock _spawn_agent at class level (can't use patch.object with __slots__)
        from src.application.services.agent_polling_service import LaunchHandle

        handle = LaunchHandle(method="tmux", pane_id="%42")
        with patch(
            "src.application.services.agent_polling_service.AgentPollingService._spawn_agent",
            return_value=handle,
        ):
            run = svc._spawn_run("task-3", "test subject")

        assert run.status == PollRunStatus.RUNNING

        # Verify lifecycle has an active launch in ACTIVE state
        active = lifecycle_svc.get_active_launch("task:task-3")
        assert active is not None


class TestPollOnceCallsReconcileExpiredLeases:
    def test_calls_reconcile(self, lifecycle_svc, poll_run_repo):
        """poll_once should call reconcile_expired_leases on the lifecycle service."""
        task_svc = MagicMock()
        task_svc.list.return_value = []
        run_dir = MagicMock()

        svc = AgentPollingService(
            task_service=task_svc,
            poll_run_repo=poll_run_repo,
            run_dir=run_dir,
            lifecycle_service=lifecycle_svc,
        )

        with patch(
            "src.application.services.agent_launch_lifecycle_service"
            ".AgentLaunchLifecycleService.reconcile_expired_leases",
            return_value=[],
        ) as mock_reconcile:
            svc.poll_once()
            mock_reconcile.assert_called_once()


class TestRepeatedPollsProduceExactlyOneLaunch:
    def test_exactly_one_launch(self, lifecycle_svc, poll_run_repo, tmp_path):
        """Two consecutive polls for the same task should produce exactly 1 launch."""
        run_dir = MagicMock()
        run_dir_mock = tmp_path / "runs"
        run_dir_mock.mkdir()
        run_dir.create_run_dir.return_value = run_dir_mock

        task_svc = MagicMock()
        task = MagicMock()
        task.id = "task-unique"
        task.subject = "unique task"
        task_svc.list.return_value = [task]
        task_svc.start.return_value = True

        svc = AgentPollingService(
            task_service=task_svc,
            poll_run_repo=poll_run_repo,
            run_dir=run_dir,
            lifecycle_service=lifecycle_svc,
            max_concurrent=10,
        )

        from src.application.services.agent_polling_service import LaunchHandle

        handle = LaunchHandle(method="tmux", pane_id="%99")
        with patch(
            "src.application.services.agent_polling_service.AgentPollingService._spawn_agent",
            return_value=handle,
        ):
            run1 = svc.poll_once()

        # First poll should launch
        assert len(run1) == 1

        # Second poll should be suppressed (active launch exists)
        with patch(
            "src.application.services.agent_polling_service.AgentPollingService._spawn_agent",
            return_value=handle,
        ):
            run2 = svc.poll_once()

        assert len(run2) == 0
