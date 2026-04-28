"""Unit tests for AgentPollingService."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.agent_polling_service import (
    DEFAULT_CONCURRENCY,
    AgentPollingService,
    LaunchHandle,
)
from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)
from src.domain.entities.poll_run import PollRun, PollRunStatus
from src.infrastructure.polling.poll_run_directory import PollRunDirectory


def _make_task(
    task_id: str = "task-1",
    subject: str = "Test task",
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.APPROVED,
) -> OrchestrationTask:
    return OrchestrationTask(
        id=task_id,
        subject=subject,
        status=status,
    )


def _make_run(
    run_id: str = "run-1",
    task_id: str = "task-1",
    status: PollRunStatus = PollRunStatus.RUNNING,
) -> PollRun:
    return PollRun(
        id=run_id,
        task_id=task_id,
        agent_name="poll-agent",
        status=status,
    )


class MockRepo:
    """Mock PollRunRepository for testing."""

    def __init__(self) -> None:
        self._runs: dict[str, PollRun] = {}

    def save(self, run: PollRun) -> None:
        self._runs[run.id] = run

    def get_by_id(self, run_id: str) -> PollRun | None:
        return self._runs.get(run_id)

    def list_by_status(self, status: PollRunStatus) -> list[PollRun]:
        return [r for r in self._runs.values() if r.status == status]

    def list_active(self) -> list[PollRun]:
        return [
            r
            for r in self._runs.values()
            if r.status
            in (
                PollRunStatus.QUEUED,
                PollRunStatus.SPAWNING,
                PollRunStatus.RUNNING,
                PollRunStatus.TERMINATING,
            )
        ]

    def list_launch_blocking(self) -> list[PollRun]:
        return [
            r
            for r in self._runs.values()
            if r.status
            in (
                PollRunStatus.QUEUED,
                PollRunStatus.SPAWNING,
                PollRunStatus.RUNNING,
                PollRunStatus.TERMINATING,
                PollRunStatus.QUARANTINED,
            )
        ]

    def update_status(
        self, run_id: str, status: PollRunStatus, error_message: str | None = None
    ) -> None:
        run = self._runs.get(run_id)
        if run:
            self._runs[run_id] = replace(run, status=status, error_message=error_message)

    def remove(self, run_id: str) -> None:
        self._runs.pop(run_id, None)

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for run in self._runs.values():
            counts[run.status.value] = counts.get(run.status.value, 0) + 1
        return counts

    def record_launch_metadata(
        self,
        run_id: str,
        *,
        launch_method: str,
        pane_id: str | None = None,
        pid: int | None = None,
        pgid: int | None = None,
        launch_id: str | None = None,
    ) -> bool:
        run = self._runs.get(run_id)
        if run is None:
            return False
        self._runs[run_id] = replace(
            run,
            launch_method=launch_method,
            launch_pane_id=pane_id,
            launch_pid=pid,
            launch_pgid=pgid,
            launch_recorded_at=1,
        )
        return True


def _make_service(
    max_concurrent: int = DEFAULT_CONCURRENCY,
    task_service: MagicMock | None = None,
    repo: MockRepo | None = None,
    allow_subprocess_fallback: bool = True,
) -> tuple[AgentPollingService, MagicMock, MockRepo, MagicMock]:
    ts: MagicMock = task_service or MagicMock(spec=TaskBoardService)
    r: MockRepo = repo or MockRepo()
    rd = MagicMock(spec=PollRunDirectory)
    rd.create_run_dir.return_value = "/tmp/test-runs/test"
    rd.read_events.return_value = []

    svc = AgentPollingService(
        task_service=ts,
        poll_run_repo=r,
        run_dir=rd,
        max_concurrent=max_concurrent,
        allow_subprocess_fallback=allow_subprocess_fallback,
    )
    return svc, ts, r, rd


class TestPollOnce:
    """Tests for poll_once()."""

    def test_no_approved_tasks_returns_empty(self) -> None:
        svc, ts, _, _ = _make_service()
        ts.list.return_value = []

        result = svc.poll_once()
        assert result == []

    def test_one_approved_task_creates_one_run(self) -> None:
        svc, ts, repo, rd = _make_service()
        task = _make_task("task-1")
        ts.list.return_value = [task]
        ts.start.return_value = None

        with patch.object(
            AgentPollingService,
            "_spawn_agent",
            return_value=LaunchHandle(method="tmux", pane_id="%1"),
        ):
            runs = svc.poll_once()
        assert len(runs) == 1
        assert runs[0].task_id == "task-1"
        assert runs[0].status == PollRunStatus.RUNNING
        # Verify side effects
        ts.start.assert_called_once_with("task-1", owner="poll-agent")
        rd.write_status.assert_called_once()
        rd.append_event.assert_called()

    def test_three_approved_max_two_spawns_two(self) -> None:
        svc, ts, repo, rd = _make_service(max_concurrent=2)
        tasks = [_make_task(f"task-{i}") for i in range(3)]
        ts.list.return_value = tasks

        with patch.object(
            AgentPollingService,
            "_spawn_agent",
            return_value=LaunchHandle(method="tmux", pane_id="%1"),
        ):
            runs = svc.poll_once()
        assert len(runs) == 2

    def test_at_cap_returns_empty(self) -> None:
        svc, ts, repo, rd = _make_service(max_concurrent=1)
        # Pre-populate active run
        repo.save(_make_run("run-active", status=PollRunStatus.RUNNING))

        ts.list.return_value = [_make_task("task-new")]
        runs = svc.poll_once()
        assert len(runs) == 0

    def test_task_already_has_active_run_skipped(self) -> None:
        svc, ts, repo, rd = _make_service()
        # Pre-populate active run for task-1
        repo.save(_make_run("run-1", task_id="task-1", status=PollRunStatus.RUNNING))

        ts.list.return_value = [_make_task("task-1")]
        runs = svc.poll_once()
        assert len(runs) == 0

    def test_quarantined_run_blocks_relaunch_across_cycles(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-q", task_id="task-1", status=PollRunStatus.QUARANTINED))
        ts.list.return_value = [_make_task("task-1")]

        first = svc.poll_once()
        second = svc.poll_once()

        assert first == []
        assert second == []
        ts.start.assert_not_called()

    def test_ambiguous_spawn_result_is_quarantined(self) -> None:
        svc, ts, repo, rd = _make_service()
        task = _make_task("task-1")
        ts.list.return_value = [task]
        with patch.object(AgentPollingService, "_spawn_agent", return_value=None):
            runs = svc.poll_once()

        assert len(runs) == 1
        assert runs[0].status == PollRunStatus.QUARANTINED
        ts.start.assert_called_once_with("task-1", owner="poll-agent")

    def test_metadata_persisted_before_running(self) -> None:
        svc, ts, repo, rd = _make_service()
        task = _make_task("task-1")
        ts.list.return_value = [task]
        with patch.object(
            AgentPollingService,
            "_spawn_agent",
            return_value=LaunchHandle(method="subprocess", pid=123, pgid=123),
        ):
            runs = svc.poll_once()

        assert runs[0].status == PollRunStatus.RUNNING
        saved = repo.get_by_id(runs[0].id)
        assert saved is not None
        assert saved.launch_method == "subprocess"
        assert saved.launch_pid == 123
        assert saved.launch_pgid == 123


class TestCheckRuns:
    """Tests for check_runs()."""

    def test_no_active_runs_returns_empty(self) -> None:
        svc, ts, repo, rd = _make_service()
        runs = svc.check_runs()
        assert runs == []

    def test_active_run_completed_status(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-1", task_id="task-1", status=PollRunStatus.RUNNING))

        rd.read_status.return_value = {"status": "COMPLETED"}

        updated = svc.check_runs()
        assert len(updated) == 1
        assert updated[0].status == PollRunStatus.COMPLETED
        ts.complete.assert_called_once_with("task-1")

    def test_active_run_no_status_file_marks_failed(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-1", task_id="task-1", status=PollRunStatus.RUNNING))

        rd.read_status.return_value = None

        updated = svc.check_runs()
        assert len(updated) == 1
        assert updated[0].status == PollRunStatus.FAILED
        assert "crashed" in (updated[0].error_message or "").lower()

    def test_active_run_failed_status(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-1", task_id="task-1", status=PollRunStatus.RUNNING))

        rd.read_status.return_value = {"status": "FAILED", "error": "OOM"}

        updated = svc.check_runs()
        assert updated[0].status == PollRunStatus.FAILED


class TestCancelRun:
    """Tests for cancel_run()."""

    def test_cancel_running_run(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-1", status=PollRunStatus.RUNNING))

        result = svc.cancel_run("run-1")
        assert result.status == PollRunStatus.CANCELLED

    def test_cancel_nonexistent_raises(self) -> None:
        svc, ts, repo, rd = _make_service()

        with pytest.raises(ValueError, match="not found"):
            svc.cancel_run("nonexistent")

    def test_cancel_completed_raises(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-1", status=PollRunStatus.COMPLETED))

        with pytest.raises(ValueError, match="Cannot cancel"):
            svc.cancel_run("run-1")


class TestSpawnCleanup:
    """Tests for agent cleanup on terminal states."""

    def test_complete_run_terminates_spawned_subprocess(self) -> None:
        svc, ts, repo, rd = _make_service()
        rd.read_events.return_value = [
            {"type": "agent_spawned", "pid": 4242, "method": "subprocess"}
        ]

        with patch.object(AgentPollingService, "_terminate_pid") as terminate_pid:
            svc._complete_run("run-1", "task-1")
            terminate_pid.assert_called_once_with(4242)

    def test_fail_run_terminates_spawned_tmux_pane(self) -> None:
        svc, ts, repo, rd = _make_service()
        rd.read_events.return_value = [
            {"type": "agent_spawned", "pane_id": "%42", "method": "tmux"}
        ]

        with patch("subprocess.run") as run_mock:
            svc._fail_run("run-1", "boom")
            run_mock.assert_called_once()

    def test_cancel_run_terminates_spawned_subprocess(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("run-1", status=PollRunStatus.RUNNING))
        rd.read_events.return_value = [
            {"type": "agent_spawned", "pid": "4242", "method": "subprocess"}
        ]

        with patch.object(AgentPollingService, "_terminate_pid") as terminate_pid:
            svc.cancel_run("run-1")
            terminate_pid.assert_called_once_with(4242)


class TestGetStatusSummary:
    """Tests for get_status_summary()."""

    def test_empty_summary(self) -> None:
        svc, ts, repo, rd = _make_service()
        summary = svc.get_status_summary()
        # count_by_status returns empty dict when no runs exist
        assert summary == {}

    def test_summary_with_runs(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("r1", status=PollRunStatus.RUNNING))
        repo.save(_make_run("r2", status=PollRunStatus.COMPLETED))
        repo.save(_make_run("r3", status=PollRunStatus.FAILED))

        summary = svc.get_status_summary()
        assert summary["RUNNING"] == 1
        assert summary["COMPLETED"] == 1
        assert summary["FAILED"] == 1
        # QUEUED not present — count_by_status only returns existing statuses


class TestGetActiveRuns:
    """Tests for get_active_runs()."""

    def test_returns_active_only(self) -> None:
        svc, ts, repo, rd = _make_service()
        repo.save(_make_run("r1", status=PollRunStatus.RUNNING))
        repo.save(_make_run("r2", status=PollRunStatus.QUEUED))
        repo.save(_make_run("r3", status=PollRunStatus.COMPLETED))

        active = svc.get_active_runs()
        ids = {r.id for r in active}
        assert ids == {"r1", "r2"}
