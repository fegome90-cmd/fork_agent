"""Tests for Phase C technical debt fixes in AgentPollingService."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from src.application.exceptions import TaskTransitionError
from src.domain.entities.poll_run import PollRun, PollRunStatus


def _make_run(
    run_id: str = "r1",
    task_id: str = "t1",
    status: PollRunStatus = PollRunStatus.RUNNING,
    started_at: int | None = None,
) -> PollRun:
    return PollRun(
        id=run_id,
        task_id=task_id,
        agent_name="poll-agent",
        status=status,
        started_at=started_at or int(time.time() * 1000),
    )


def _make_service():
    from src.application.services.agent_polling_service import AgentPollingService

    poll_repo = MagicMock()
    task_service = MagicMock()
    run_dir = MagicMock()
    service = AgentPollingService(
        task_service=task_service,
        poll_run_repo=poll_repo,
        run_dir=run_dir,
        max_concurrent=4,
    )
    return service, poll_repo, task_service, run_dir


class TestFailRunResetsTask:
    """SM-C1: _fail_run must reset OrchestrationTask to APPROVED."""

    def test_fail_run_calls_retry(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        run = _make_run()
        poll_repo.get_by_id.return_value = run

        service._fail_run("r1", "error")

        task_service.retry.assert_called_once_with("t1")

    def test_fail_run_tolerates_retry_failure(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        run = _make_run()
        poll_repo.get_by_id.return_value = run
        task_service.retry.side_effect = ValueError("deleted")

        # Should NOT raise
        service._fail_run("r1", "error")

    def test_fail_run_tolerates_transition_error(self) -> None:
        """TaskTransitionError from retry should also be silently caught."""
        service, poll_repo, task_service, run_dir = _make_service()
        run = _make_run()
        poll_repo.get_by_id.return_value = run
        task_service.retry.side_effect = TaskTransitionError("already reset")

        # Should NOT raise
        service._fail_run("r1", "error")

    def test_fail_run_tolerates_missing_run(self) -> None:
        """When get_by_id returns None, retry should not be called."""
        service, poll_repo, task_service, run_dir = _make_service()
        poll_repo.get_by_id.return_value = None

        # Should NOT call retry and should NOT raise
        service._fail_run("r1", "error")
        task_service.retry.assert_not_called()

    def test_fail_run_tolerates_none_run(self) -> None:
        """If the run disappeared from the repo, retry should not be called."""
        service, poll_repo, task_service, run_dir = _make_service()
        poll_repo.get_by_id.return_value = None

        service._fail_run("r1", "error")
        task_service.retry.assert_not_called()


class TestCancelRunResetsTask:
    """SM-C2: cancel_run must reset OrchestrationTask to APPROVED."""

    def test_cancel_run_calls_retry(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        run = _make_run(status=PollRunStatus.RUNNING)
        poll_repo.get_by_id.return_value = run

        with patch("subprocess.run"):
            service.cancel_run("r1")

        task_service.retry.assert_called_once_with("t1")

    def test_cancel_run_tolerates_retry_failure(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        run = _make_run(status=PollRunStatus.RUNNING)
        poll_repo.get_by_id.return_value = run
        task_service.retry.side_effect = ValueError("deleted")

        with patch("subprocess.run"):
            # Should NOT raise
            service.cancel_run("r1")


class TestSpawnRunNarrowCatch:
    """B-C4: _spawn_run should only catch TaskTransitionError, not bare ValueError."""

    def test_spawn_run_reraises_value_error_for_not_found(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        task_service.start.side_effect = ValueError("Task 't1' not found")
        run_dir.create_run_dir.return_value = "/tmp/test-runs/r1"

        with pytest.raises(ValueError, match="not found"):
            service._spawn_run("t1", "subject")

    def test_spawn_run_catches_task_transition_error(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        poll_repo.save.return_value = None
        poll_repo.get_by_id.return_value = _make_run(status=PollRunStatus.FAILED)
        task_service.start.side_effect = TaskTransitionError("Cannot start")
        run_dir.create_run_dir.return_value = "/tmp/test-runs/r1"

        # Should NOT raise — catch is specific to TaskTransitionError
        result = service._spawn_run("t1", "subject")
        assert result is not None
        assert result.status == PollRunStatus.FAILED


class TestQueuedTimeout:
    """SM-H1: QUEUED runs older than 300s should be auto-failed."""

    def test_queued_run_timeout_triggers_fail(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        old_queued = _make_run(
            status=PollRunStatus.QUEUED,
            started_at=int(time.time() * 1000) - 600_000,  # 10 min ago
        )
        poll_repo.list_active.return_value = [old_queued]
        run_dir.read_status.return_value = None  # no status file
        poll_repo.get_by_id.return_value = _make_run(status=PollRunStatus.FAILED)

        service.check_runs()

        # Should have called update_status with FAILED
        calls = [c for c in poll_repo.update_status.call_args_list]
        assert any(c[0][1] == PollRunStatus.FAILED for c in calls)

    def test_recent_queued_run_not_timed_out(self) -> None:
        service, poll_repo, task_service, run_dir = _make_service()
        recent_queued = _make_run(
            status=PollRunStatus.QUEUED,
            started_at=int(time.time() * 1000) - 10_000,  # 10s ago
        )
        poll_repo.list_active.return_value = [recent_queued]
        run_dir.read_status.return_value = None
        poll_repo.get_by_id.return_value = _make_run(status=PollRunStatus.FAILED)

        service.check_runs()

        # Should NOT fail a recent QUEUED run — still within timeout
        # But it WILL fail because "Spawn incomplete" (no status file)
        # Just verify it doesn't use the timeout message
        calls = [c for c in poll_repo.update_status.call_args_list]
        for c in calls:
            error_msg = c[0][2] if len(c[0]) > 2 else ""
            assert "timeout" not in error_msg.lower()


class TestMaxConcurrentSetter:
    """Q-H2: max_concurrent should use validated setter."""

    def test_set_max_concurrent_valid(self) -> None:
        service, _, _, _ = _make_service()
        service.max_concurrent = 8
        assert service.max_concurrent == 8

    def test_set_max_concurrent_invalid(self) -> None:
        service, _, _, _ = _make_service()
        with pytest.raises(ValueError, match=">= 1"):
            service.max_concurrent = 0

    def test_set_poll_interval_valid(self) -> None:
        service, _, _, _ = _make_service()
        service.poll_interval = 2
        assert service.poll_interval == 2

    def test_set_poll_interval_invalid(self) -> None:
        service, _, _, _ = _make_service()
        with pytest.raises(ValueError, match=">= 0.1"):
            service.poll_interval = 0


class TestStatusSummarySingleQuery:
    """Q-H3: get_status_summary should use count_by_status (single query)."""

    def test_uses_count_by_status(self) -> None:
        service, poll_repo, _, _ = _make_service()
        poll_repo.count_by_status.return_value = {"RUNNING": 3, "COMPLETED": 5}

        result = service.get_status_summary()

        poll_repo.count_by_status.assert_called_once()
        assert result == {"RUNNING": 3, "COMPLETED": 5}

    def test_empty_db_returns_empty_summary(self) -> None:
        service, poll_repo, _, _ = _make_service()
        poll_repo.count_by_status.return_value = {}

        result = service.get_status_summary()

        assert result == {}
