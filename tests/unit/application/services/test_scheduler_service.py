"""Unit tests for SchedulerService."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, create_autospec

import pytest

from src.application.services.scheduler_service import SchedulerService
from src.domain.entities.scheduled_task import ScheduledTask, TaskStatus
from src.domain.ports.scheduled_task_repository import ScheduledTaskRepository


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock ScheduledTaskRepository."""
    return create_autospec(ScheduledTaskRepository)


@pytest.fixture
def scheduler_service(mock_repository: MagicMock) -> SchedulerService:
    """Create a SchedulerService with mock repository."""
    return SchedulerService(repository=mock_repository)


class TestSchedulerServiceCreateTask:
    """Tests for create_task method."""

    def test_create_task_success(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test successful task creation."""
        task_id = "test-task-001"
        scheduled_at = int(time.time() * 1000) + 3600000  # 1 hour from now
        action = "test_action"
        context = {"key": "value"}

        result = scheduler_service.create_task(
            task_id=task_id,
            scheduled_at=scheduled_at,
            action=action,
            context=context,
        )

        assert result.id == task_id
        assert result.action == action
        assert result.scheduled_at == scheduled_at
        assert result.status == TaskStatus.PENDING
        assert result.context == context
        mock_repository.create.assert_called_once()

    def test_create_task_without_context(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test task creation without context."""
        task_id = "test-task-002"
        scheduled_at = int(time.time() * 1000) + 3600000

        result = scheduler_service.create_task(
            task_id=task_id,
            scheduled_at=scheduled_at,
            action="simple_action",
        )

        assert result.context is None
        mock_repository.create.assert_called_once()


class TestSchedulerServiceGetTask:
    """Tests for get_task method."""

    def test_get_task_found(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test getting an existing task."""
        task_id = "test-task-001"
        expected_task = ScheduledTask(
            id=task_id,
            scheduled_at=1234567890000,
            action="test_action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )
        mock_repository.get_by_id.return_value = expected_task

        result = scheduler_service.get_task(task_id)

        assert result == expected_task
        mock_repository.get_by_id.assert_called_once_with(task_id)

    def test_get_task_not_found(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test getting a non-existent task."""
        mock_repository.get_by_id.return_value = None

        result = scheduler_service.get_task("non-existent")

        assert result is None
        mock_repository.get_by_id.assert_called_once_with("non-existent")


class TestSchedulerServiceGetPendingTasks:
    """Tests for get_pending_tasks method."""

    def test_get_pending_tasks_returns_list(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test getting pending tasks."""
        expected_tasks = [
            ScheduledTask(
                id="task-1",
                scheduled_at=1234567890000,
                action="action1",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            ),
            ScheduledTask(
                id="task-2",
                scheduled_at=1234567891000,
                action="action2",
                status=TaskStatus.PENDING,
                created_at=1234567891000,
            ),
        ]
        mock_repository.get_pending.return_value = expected_tasks

        result = scheduler_service.get_pending_tasks()

        assert result == expected_tasks
        mock_repository.get_pending.assert_called_once()


class TestSchedulerServiceGetOverdueTasks:
    """Tests for get_overdue_tasks method."""

    def test_get_overdue_tasks(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test getting overdue tasks."""
        current_time = int(time.time() * 1000)
        expected_tasks = [
            ScheduledTask(
                id="overdue-task",
                scheduled_at=current_time - 60000,
                action="overdue_action",
                status=TaskStatus.PENDING,
                created_at=current_time - 120000,
            ),
        ]
        mock_repository.get_overdue.return_value = expected_tasks

        result = scheduler_service.get_overdue_tasks()

        assert result == expected_tasks
        called_time = mock_repository.get_overdue.call_args[0][0]
        assert abs(called_time - current_time) <= 1  # allow 1ms drift


class TestSchedulerServiceMarkCompleted:
    """Tests for mark_completed method."""

    def test_mark_completed_success(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test marking a task as completed."""
        task_id = "test-task-001"

        scheduler_service.mark_completed(task_id)

        mock_repository.update_status.assert_called_once_with(task_id, TaskStatus.EXECUTED)


class TestSchedulerServiceMarkFailed:
    """Tests for mark_failed method."""

    def test_mark_failed_success(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test marking a task as failed."""
        task_id = "test-task-001"

        scheduler_service.mark_failed(task_id)

        mock_repository.update_status.assert_called_once_with(task_id, TaskStatus.FAILED)


class TestSchedulerServiceCancelTask:
    """Tests for cancel_task method."""

    def test_cancel_task_success(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test cancelling a task."""
        task_id = "test-task-001"

        scheduler_service.cancel_task(task_id)

        mock_repository.update_status.assert_called_once_with(task_id, TaskStatus.CANCELLED)


class TestSchedulerServiceDeleteTask:
    """Tests for delete_task method."""

    def test_delete_task_success(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test deleting a task."""
        task_id = "test-task-001"

        scheduler_service.delete_task(task_id)

        mock_repository.delete.assert_called_once_with(task_id)


class TestSchedulerServiceGetAllTasks:
    """Tests for get_all_tasks method."""

    def test_get_all_tasks(
        self, scheduler_service: SchedulerService, mock_repository: MagicMock
    ) -> None:
        """Test getting all tasks."""
        expected_tasks = [
            ScheduledTask(
                id="task-1",
                scheduled_at=1234567890000,
                action="action1",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            ),
            ScheduledTask(
                id="task-2",
                scheduled_at=1234567891000,
                action="action2",
                status=TaskStatus.EXECUTED,
                created_at=1234567891000,
            ),
        ]
        mock_repository.get_all.return_value = expected_tasks

        result = scheduler_service.get_all_tasks()

        assert result == expected_tasks
        mock_repository.get_all.assert_called_once()
