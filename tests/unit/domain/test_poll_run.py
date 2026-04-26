"""Unit tests for PollRun entity."""

from __future__ import annotations

import pytest

from src.domain.entities.poll_run import PollRun, PollRunStatus


class TestPollRunStatus:
    """Tests for PollRunStatus enum."""

    def test_all_statuses_exist(self) -> None:
        expected = {
            "QUEUED",
            "SPAWNING",
            "RUNNING",
            "TERMINATING",
            "QUARANTINED",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }
        actual = {s.value for s in PollRunStatus}
        assert actual == expected

    def test_str_enum_behavior(self) -> None:
        assert PollRunStatus.QUEUED == "QUEUED"
        assert PollRunStatus.RUNNING == "RUNNING"


class TestPollRunCreation:
    """Tests for PollRun entity creation."""

    def test_minimal_creation(self) -> None:
        run = PollRun(
            id="abc123",
            task_id="task-1",
            agent_name="agent-x",
            status=PollRunStatus.QUEUED,
        )
        assert run.id == "abc123"
        assert run.task_id == "task-1"
        assert run.agent_name == "agent-x"
        assert run.status == PollRunStatus.QUEUED
        assert run.started_at is None
        assert run.ended_at is None
        assert run.poll_run_dir is None
        assert run.error_message is None

    def test_full_creation(self) -> None:
        run = PollRun(
            id="run-1",
            task_id="task-1",
            agent_name="agent-x",
            status=PollRunStatus.RUNNING,
            started_at=1000,
            ended_at=None,
            poll_run_dir="/tmp/runs/run-1",
            error_message=None,
        )
        assert run.started_at == 1000
        assert run.poll_run_dir == "/tmp/runs/run-1"

    def test_frozen(self) -> None:
        run = PollRun(id="r1", task_id="t1", agent_name="a1", status=PollRunStatus.QUEUED)
        with pytest.raises(AttributeError):
            run.status = PollRunStatus.RUNNING  # type: ignore[misc]

    def test_empty_task_id_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            PollRun(id="r1", task_id="", agent_name="a1", status=PollRunStatus.QUEUED)

    def test_empty_agent_name_raises(self) -> None:
        with pytest.raises(ValueError, match="agent_name"):
            PollRun(id="r1", task_id="t1", agent_name="", status=PollRunStatus.QUEUED)

    def test_non_string_task_id_raises(self) -> None:
        with pytest.raises(ValueError, match="task_id"):
            PollRun(id="r1", task_id=123, agent_name="a1", status=PollRunStatus.QUEUED)  # type: ignore[arg-type]

    def test_non_string_agent_name_raises(self) -> None:
        with pytest.raises(ValueError, match="agent_name"):
            PollRun(id="r1", task_id="t1", agent_name=123, status=PollRunStatus.QUEUED)  # type: ignore[arg-type]

    def test_invalid_status_type_raises(self) -> None:
        with pytest.raises(TypeError, match="PollRunStatus"):
            PollRun(id="r1", task_id="t1", agent_name="a1", status="INVALID")  # type: ignore[arg-type]

    def test_negative_started_at_raises(self) -> None:
        with pytest.raises(ValueError, match="started_at"):
            PollRun(
                id="r1", task_id="t1", agent_name="a1", status=PollRunStatus.RUNNING, started_at=-1
            )

    def test_negative_ended_at_raises(self) -> None:
        with pytest.raises(ValueError, match="ended_at"):
            PollRun(
                id="r1", task_id="t1", agent_name="a1", status=PollRunStatus.COMPLETED, ended_at=-1
            )


def _make_run(status: PollRunStatus) -> PollRun:
    """Helper to create a PollRun with a given status."""
    return PollRun(id="r1", task_id="t1", agent_name="a1", status=status)


class TestPollRunTransitions:
    """Tests for can_transition_to."""

    @pytest.mark.parametrize(
        "source",
        [
            PollRunStatus.COMPLETED,
            PollRunStatus.FAILED,
            PollRunStatus.CANCELLED,
        ],
    )
    def test_terminal_states_allow_nothing(self, source: PollRunStatus) -> None:
        run = _make_run(source)
        for target in PollRunStatus:
            assert not run.can_transition_to(target), (
                f"{source.value} should not transition to {target.value}"
            )

    def test_queued_to_spawning(self) -> None:
        assert _make_run(PollRunStatus.QUEUED).can_transition_to(PollRunStatus.SPAWNING)

    def test_queued_to_cancelled(self) -> None:
        assert _make_run(PollRunStatus.QUEUED).can_transition_to(PollRunStatus.CANCELLED)

    def test_queued_cannot_complete(self) -> None:
        assert not _make_run(PollRunStatus.QUEUED).can_transition_to(PollRunStatus.COMPLETED)

    def test_queued_cannot_fail(self) -> None:
        assert not _make_run(PollRunStatus.QUEUED).can_transition_to(PollRunStatus.FAILED)

    def test_queued_cannot_go_running_directly(self) -> None:
        assert not _make_run(PollRunStatus.QUEUED).can_transition_to(PollRunStatus.RUNNING)

    def test_running_to_completed(self) -> None:
        assert _make_run(PollRunStatus.RUNNING).can_transition_to(PollRunStatus.COMPLETED)

    def test_running_to_failed(self) -> None:
        assert _make_run(PollRunStatus.RUNNING).can_transition_to(PollRunStatus.FAILED)

    def test_running_to_cancelled(self) -> None:
        assert _make_run(PollRunStatus.RUNNING).can_transition_to(PollRunStatus.CANCELLED)

    def test_running_to_terminating(self) -> None:
        assert _make_run(PollRunStatus.RUNNING).can_transition_to(PollRunStatus.TERMINATING)

    def test_running_cannot_requeue(self) -> None:
        assert not _make_run(PollRunStatus.RUNNING).can_transition_to(PollRunStatus.QUEUED)

    @pytest.mark.parametrize(
        "source,valid_targets",
        [
            (
                PollRunStatus.QUEUED,
                {PollRunStatus.SPAWNING, PollRunStatus.CANCELLED, PollRunStatus.QUARANTINED},
            ),
            (
                PollRunStatus.RUNNING,
                {
                    PollRunStatus.TERMINATING,
                    PollRunStatus.COMPLETED,
                    PollRunStatus.FAILED,
                    PollRunStatus.CANCELLED,
                },
            ),
        ],
    )
    def test_exhaustive_transitions(
        self, source: PollRunStatus, valid_targets: set[PollRunStatus]
    ) -> None:
        run = _make_run(source)
        for target in PollRunStatus:
            expected = target in valid_targets
            actual = run.can_transition_to(target)
            assert actual == expected, (
                f"{source.value}→{target.value}: expected {expected}, got {actual}"
            )
