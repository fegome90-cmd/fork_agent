"""Unit tests for TaskBoardService."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW_MS = int(time.time() * 1000)
TASK_ID = "a" * 32


def _make_task(
    task_id: str = TASK_ID,
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.PENDING,
    **overrides: object,
) -> OrchestrationTask:
    defaults: dict[str, object] = {
        "id": task_id,
        "subject": "Test task",
        "status": status,
        "created_at": NOW_MS,
        "updated_at": NOW_MS,
    }
    defaults.update(overrides)
    return OrchestrationTask(**defaults)  # type: ignore[arg-type]


def _make_service(repo: MagicMock | None = None) -> tuple[TaskBoardService, MagicMock]:
    mock_repo = repo if repo is not None else MagicMock()
    mock_repo.cas_save.return_value = True
    service = TaskBoardService(repo=mock_repo)  # type: ignore[arg-type]
    return service, mock_repo


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_generates_uuid4_and_saves_pending(self) -> None:
        service, repo = _make_service()
        test_uuid = "b" * 32

        with patch("src.application.services.task_board_service.uuid") as mock_uuid:
            mock_uuid.uuid4.return_value = MagicMock(hex=test_uuid)
            with patch("src.application.services.task_board_service.time") as mock_time:
                mock_time.time.return_value = NOW_MS / 1000
                task = service.create(subject="New task", description="desc", owner="me")

        assert task.id == test_uuid
        assert task.subject == "New task"
        assert task.description == "desc"
        assert task.owner == "me"
        assert task.status == OrchestrationTaskStatus.PENDING
        repo.save.assert_called_once()
        saved = repo.save.call_args[0][0]
        assert saved.status == OrchestrationTaskStatus.PENDING

    def test_create_with_defaults(self) -> None:
        service, repo = _make_service()

        with patch("src.application.services.task_board_service.uuid") as mock_uuid:
            mock_uuid.uuid4.return_value = MagicMock(hex="c" * 32)
            with patch("src.application.services.task_board_service.time") as mock_time:
                mock_time.time.return_value = NOW_MS / 1000
                task = service.create(subject="Minimal task")

        assert task.description is None
        assert task.owner is None
        assert task.status == OrchestrationTaskStatus.PENDING


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_returns_task(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task()
        result = service.get(TASK_ID)
        assert result is not None
        assert result.id == TASK_ID
        repo.get_by_id.assert_called_once_with(TASK_ID)

    def test_get_returns_none_when_not_found(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        assert service.get(TASK_ID) is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestList:
    def test_list_all(self) -> None:
        service, repo = _make_service()
        task = _make_task()
        repo.list_all.return_value = [task]
        result = service.list()
        assert len(result) == 1
        repo.list_all.assert_called_once()

    def test_list_by_status(self) -> None:
        service, repo = _make_service()
        task = _make_task(status=OrchestrationTaskStatus.PENDING)
        repo.list_by_status.return_value = [task]
        result = service.list(status=OrchestrationTaskStatus.PENDING)
        assert len(result) == 1
        repo.list_by_status.assert_called_with(OrchestrationTaskStatus.PENDING)

    def test_list_by_owner(self) -> None:
        service, repo = _make_service()
        task = _make_task(owner="alice")
        repo.list_by_owner.return_value = [task]
        result = service.list(owner="alice")
        assert len(result) == 1
        repo.list_by_owner.assert_called_with("alice")

    def test_list_default_excludes_deleted(self) -> None:
        """list() without include_deleted filters out DELETED tasks."""
        service, repo = _make_service()
        active = _make_task(status=OrchestrationTaskStatus.PENDING)
        deleted = _make_task(task_id="d" * 32, status=OrchestrationTaskStatus.DELETED)
        repo.list_all.return_value = [deleted, active]
        result = service.list()
        assert len(result) == 1
        assert result[0].status == OrchestrationTaskStatus.PENDING

    def test_list_include_deleted_true(self) -> None:
        """list(include_deleted=True) returns DELETED tasks too."""
        service, repo = _make_service()
        active = _make_task(status=OrchestrationTaskStatus.PENDING)
        deleted = _make_task(task_id="d" * 32, status=OrchestrationTaskStatus.DELETED)
        repo.list_all.return_value = [deleted, active]
        result = service.list(include_deleted=True)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_update_subject(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task()
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            updated = service.update(TASK_ID, subject="New subject")

        assert updated.subject == "New subject"
        repo.cas_save.assert_called_once()

    def test_update_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.update(TASK_ID, subject="X")

    def test_update_deleted_task_raises(self) -> None:
        """update() on DELETED task raises ValueError."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.DELETED)
        with pytest.raises(ValueError, match="Cannot update deleted"):
            service.update(TASK_ID, subject="X")

    def test_update_can_clear_description_to_none(self) -> None:
        """update() with description=None explicitly clears the field."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(description="old desc")
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            updated = service.update(TASK_ID, description=None)

        assert updated.description is None
        repo.cas_save.assert_called_once()

    def test_update_all_fields_simultaneously(self) -> None:
        """update() can change subject, description, and owner at once."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(
            subject="Old subject", description="Old desc", owner="old-owner"
        )
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            updated = service.update(
                TASK_ID,
                subject="New subject",
                description="New desc",
                owner="new-owner",
            )

        assert updated.subject == "New subject"
        assert updated.description == "New desc"
        assert updated.owner == "new-owner"
        repo.cas_save.assert_called_once()


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestSubmitPlan:
    def test_submit_plan_transitions_pending_to_planning(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PENDING)
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.submit_plan(TASK_ID, plan_text="# Plan")

        assert result.status == OrchestrationTaskStatus.PLANNING
        assert result.plan_text == "# Plan"
        repo.cas_save.assert_called_once()

    def test_submit_plan_invalid_transition_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.APPROVED)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.submit_plan(TASK_ID, plan_text="# Plan")

    def test_submit_plan_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.submit_plan(TASK_ID, plan_text="# Plan")


class TestApprove:
    def test_approve_transitions_planning_to_approved(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PLANNING)
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.approve(TASK_ID, approved_by="reviewer")

        assert result.status == OrchestrationTaskStatus.APPROVED
        assert result.approved_by == "reviewer"
        assert result.approved_at == NOW_MS
        repo.cas_save.assert_called_once()

    def test_approve_with_requested_by(self) -> None:
        """approve() stores requested_by on the entity."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PLANNING)
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.approve(TASK_ID, approved_by="reviewer", requested_by="alice")

        assert result.requested_by == "alice"

    def test_approve_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.approve(TASK_ID, approved_by="reviewer")

    def test_approve_invalid_transition_from_pending_raises(self) -> None:
        """approve() from PENDING (not PLANNING) raises ValueError."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.approve(TASK_ID, approved_by="reviewer")


class TestReject:
    def test_reject_transitions_planning_to_pending(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(
            status=OrchestrationTaskStatus.PLANNING,
            plan_text="# Old plan",
        )
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.reject(TASK_ID)

        assert result.status == OrchestrationTaskStatus.PENDING
        assert result.plan_text is None
        repo.cas_save.assert_called_once()

    def test_reject_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.reject(TASK_ID)


class TestStart:
    def test_start_transitions_approved_to_in_progress(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.APPROVED)
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.start(TASK_ID, owner="worker")

        assert result.status == OrchestrationTaskStatus.IN_PROGRESS
        assert result.owner == "worker"
        repo.cas_save.assert_called_once()

    def test_start_blocked_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(
            status=OrchestrationTaskStatus.APPROVED,
            blocked_by=("z" * 32,),
        )
        with pytest.raises(ValueError, match="blocked"):
            service.start(TASK_ID, owner="worker")

    def test_start_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.start(TASK_ID, owner="worker")

    def test_start_invalid_transition_from_pending_raises(self) -> None:
        """start() from PENDING (not APPROVED) raises ValueError."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.start(TASK_ID, owner="worker")


class TestComplete:
    def test_complete_transitions_in_progress_to_completed(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.IN_PROGRESS)
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.complete(TASK_ID)

        assert result.status == OrchestrationTaskStatus.COMPLETED
        repo.cas_save.assert_called_once()

    def test_complete_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.complete(TASK_ID)

    def test_complete_invalid_transition_from_pending_raises(self) -> None:
        """complete() from PENDING (not IN_PROGRESS) raises ValueError."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.complete(TASK_ID)


class TestDelete:
    @pytest.mark.parametrize(
        "status",
        [
            OrchestrationTaskStatus.PENDING,
            OrchestrationTaskStatus.PLANNING,
            OrchestrationTaskStatus.APPROVED,
            OrchestrationTaskStatus.IN_PROGRESS,
            OrchestrationTaskStatus.COMPLETED,
        ],
    )
    def test_delete_transitions_any_to_deleted(self, status: OrchestrationTaskStatus) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=status)
        repo.cas_save.return_value = True
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            result = service.delete(TASK_ID)

        assert result.status == OrchestrationTaskStatus.DELETED
        repo.cas_save.assert_called_once()

    def test_delete_not_found_raises(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.delete(TASK_ID)


# ---------------------------------------------------------------------------
# updated_at
# ---------------------------------------------------------------------------


class TestUpdatedAt:
    def test_update_sets_updated_at(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task()
        new_ts = NOW_MS + 5000
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = new_ts / 1000
            result = service.update(TASK_ID, subject="Updated")

        assert result.updated_at == new_ts

    def test_submit_plan_sets_updated_at(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PENDING)
        repo.cas_save.return_value = True
        new_ts = NOW_MS + 5000
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = new_ts / 1000
            result = service.submit_plan(TASK_ID, plan_text="# Plan")

        assert result.updated_at == new_ts

    def test_complete_sets_updated_at(self) -> None:
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.IN_PROGRESS)
        repo.cas_save.return_value = True
        new_ts = NOW_MS + 5000
        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = new_ts / 1000
            result = service.complete(TASK_ID)

        assert result.updated_at == new_ts


# ---------------------------------------------------------------------------
# resolve_blockers (M9)
# ---------------------------------------------------------------------------


class TestResolveBlockers:
    def test_resolve_after_complete_returns_unblocked_task(self) -> None:
        """Complete task A; task B (blocked by A only) should be returned."""
        service, repo = _make_service()
        task_b_id = "b" * 32
        completed_a = _make_task(
            task_id=TASK_ID,
            status=OrchestrationTaskStatus.COMPLETED,
        )
        blocked_b = _make_task(
            task_id=task_b_id,
            status=OrchestrationTaskStatus.APPROVED,
            blocked_by=(TASK_ID,),
        )
        # list_blocked returns B (has non-empty blocked_by)
        repo.list_blocked.return_value = [blocked_b]
        # get_by_ids returns the completed blocker A
        repo.get_by_ids.return_value = [completed_a]

        result = service.resolve_blockers(TASK_ID)
        assert task_b_id in result

    def test_resolve_partial_blockers_does_not_return(self) -> None:
        """Task B blocked by A and C — A completed but C still PENDING → B not returned."""
        service, repo = _make_service()
        task_b_id = "b" * 32
        task_c_id = "c" * 32
        completed_a = _make_task(
            task_id=TASK_ID,
            status=OrchestrationTaskStatus.COMPLETED,
        )
        pending_c = _make_task(
            task_id=task_c_id,
            status=OrchestrationTaskStatus.PENDING,
        )
        blocked_b = _make_task(
            task_id=task_b_id,
            status=OrchestrationTaskStatus.APPROVED,
            blocked_by=(TASK_ID, task_c_id),
        )
        repo.list_blocked.return_value = [blocked_b]
        repo.get_by_ids.return_value = [completed_a, pending_c]

        result = service.resolve_blockers(TASK_ID)
        assert task_b_id not in result


# ---------------------------------------------------------------------------
# Concurrent approve + delete TOCTOU (M9)
# ---------------------------------------------------------------------------


class TestConcurrentTransitions:
    def test_approve_then_delete_fails_on_second(self) -> None:
        """After approve succeeds, a delete with stale status fails (cas_save returns False)."""
        service, repo = _make_service()
        repo.get_by_id.return_value = _make_task(status=OrchestrationTaskStatus.PLANNING)
        # First call (approve) succeeds
        repo.cas_save.return_value = True

        with patch("src.application.services.task_board_service.time") as mock_time:
            mock_time.time.return_value = NOW_MS / 1000
            service.approve(TASK_ID, approved_by="reviewer")

        # Second call (delete) — cas_save returns False because status changed
        repo.cas_save.return_value = False
        with pytest.raises(ValueError, match="modified concurrently"):
            service.delete(TASK_ID)
