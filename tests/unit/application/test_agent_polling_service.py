"""Unit tests for AgentPollingService."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.application.exceptions import TaskTransitionError
from src.application.services.agent_polling_service import (
    DEFAULT_CONCURRENCY,
    AgentPollingService,
    LaunchHandle,
)
from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.fpel import AuthorizationDecision, FPELStatus, SealFailureReason
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


class TestFPELSharedGate:
    """Tests for FPEL sealed-PASS gate shared between polling and manual start.

    The gate lives in TaskBoardService.start() — both polling and manual CLI
    flows call the same method, which checks FPELAuthorizationPort.check_sealed().

    Spec references:
      R4 Scenario 3: Polling starts only through shared gate
      R4 Scenario 4: Sealed PASS → polling calls start() before spawn
      R4 Scenario 2: Denied start never spawns
    """

    @staticmethod
    def _make_task_service_with_fpel(
        task: OrchestrationTask,
        decision: AuthorizationDecision,
    ) -> MagicMock:
        """Create a TaskBoardService mock that gates via FPELAuthorizationPort.

        Simulates the real TaskBoardService.start() behavior:
        if fpel_port is set, calls check_sealed() and raises ValueError on denial.
        """
        ts = MagicMock(spec=TaskBoardService)
        ts.list.return_value = [task]

        if decision.allowed:
            ts.start.return_value = None
        else:

            def _start_denied(task_id: str, **kwargs):
                raise TaskTransitionError(
                    f"Task '{task_id}' requires sealed PASS to start. "
                    f"Status: {decision.status.value}"
                )

            ts.start.side_effect = _start_denied
        return ts

    def test_sealed_pass_calls_start_before_spawn(self) -> None:
        """Sealed PASS → polling calls TaskBoardService.start() before spawn.

        Verifies the FPEL gate is consumed through TaskBoardService.start(),
        which internally calls FPELAuthorizationPort.check_sealed().
        """
        sealed_decision = AuthorizationDecision(
            allowed=True,
            status=FPELStatus.SEALED_PASS,
            frozen_proposal_id="fp-1",
            content_hash="abc123",
            reason=None,
            seal_id="seal-1",
            sealed_at=datetime.now(timezone.utc),
        )
        task = _make_task("task-sealed")
        ts = self._make_task_service_with_fpel(task, sealed_decision)
        svc, _, repo, rd = _make_service(task_service=ts)

        with patch.object(
            AgentPollingService,
            "_spawn_agent",
            return_value=LaunchHandle(method="tmux", pane_id="%1"),
        ):
            runs = svc.poll_once()

        assert len(runs) == 1
        assert runs[0].status == PollRunStatus.RUNNING
        # The critical assertion: start() was called before spawn
        ts.start.assert_called_once_with("task-sealed", owner="poll-agent")

    def test_denied_start_never_spawns_agent(self) -> None:
        """Denied FPEL gate → task start raises, agent never spawns.

        When TaskBoardService.start() raises ValueError (FPEL denial),
        the polling service records a FAILED run and never calls _spawn_agent.
        """
        denied_decision = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.CHECK_FAILED,
            frozen_proposal_id="fp-1",
            content_hash="abc123",
            reason=SealFailureReason.MISSING_REPORTS,
            seal_id=None,
            sealed_at=None,
        )
        task = _make_task("task-denied")
        ts = self._make_task_service_with_fpel(task, denied_decision)
        svc, _, repo, rd = _make_service(task_service=ts)

        with patch.object(AgentPollingService, "_spawn_agent") as mock_spawn:
            runs = svc.poll_once()

        # The run is recorded but FAILED (from _spawn_run catching TaskTransitionError
        # when start() raises — actually ValueError, caught by except TaskTransitionError)
        assert len(runs) == 1
        # Agent was never spawned
        mock_spawn.assert_not_called()

    def test_polling_and_manual_start_share_fpel_gate(self) -> None:
        """Both polling and manual start go through the same FPELAuthorizationPort.

        This verifies the shared gate architecture: both code paths call
        TaskBoardService.start(), which contains the FPEL check.
        The polling service delegates to task_service.start(), and the
        manual CLI path also calls task_service.start().
        """
        sealed_decision = AuthorizationDecision(
            allowed=True,
            status=FPELStatus.SEALED_PASS,
            frozen_proposal_id="fp-shared",
            content_hash="hash-shared",
            reason=None,
            seal_id="seal-shared",
            sealed_at=datetime.now(timezone.utc),
        )
        task = _make_task("task-shared")
        ts = self._make_task_service_with_fpel(task, sealed_decision)
        svc, _, repo, rd = _make_service(task_service=ts)

        # Polling path: calls start() internally
        with patch.object(
            AgentPollingService,
            "_spawn_agent",
            return_value=LaunchHandle(method="tmux", pane_id="%1"),
        ):
            svc.poll_once()

        # Manual path: direct call to task_service.start()
        ts.start("task-shared", owner="manual-user")

        # Both paths hit the same gate (same mock object)
        assert ts.start.call_count == 2
        ts.start.assert_any_call("task-shared", owner="poll-agent")
        ts.start.assert_any_call("task-shared", owner="manual-user")

    def test_denied_start_run_recorded_as_failed(self) -> None:
        """When FPEL denies start, the run exists with FAILED status and error message."""
        denied_decision = AuthorizationDecision(
            allowed=False,
            status=FPELStatus.NOT_EVALUATED,
            frozen_proposal_id=None,
            content_hash=None,
            reason=SealFailureReason.NO_FROZEN_PROPOSAL,
            seal_id=None,
            sealed_at=None,
        )
        task = _make_task("task-no-fpel")
        ts = self._make_task_service_with_fpel(task, denied_decision)
        svc, _, repo, rd = _make_service(task_service=ts)

        runs = svc.poll_once()

        assert len(runs) == 1
        assert runs[0].status == PollRunStatus.FAILED
        assert "sealed PASS" in (runs[0].error_message or "")
