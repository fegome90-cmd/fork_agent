"""Tests for schedule CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.domain.entities.scheduled_task import ScheduledTask, TaskStatus
from src.interfaces.cli.commands import schedule

runner = CliRunner()


class TestScheduleAddCommand:
    """Tests for schedule add command."""

    def test_add_task_success(self) -> None:
        """Test adding a scheduled task successfully."""
        mock_task = ScheduledTask(
            id="test-task-id",
            scheduled_at=1234567890000,
            action="echo hello",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.create_task.return_value = mock_task
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["add", "echo hello", "60"])

            assert result.exit_code == 0
            assert "Scheduled task" in result.output
            assert "echo hello" in result.output

    def test_add_task_with_context(self) -> None:
        """Test adding a task with JSON context."""
        mock_task = ScheduledTask(
            id="test-task-id",
            scheduled_at=1234567890000,
            action="echo hello",
            context={"key": "value"},
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.create_task.return_value = mock_task
            mock_get_service.return_value = mock_service

            result = runner.invoke(
                schedule.app,
                ["add", "echo hello", "60", "--context", '{"key": "value"}'],
            )

            assert result.exit_code == 0
            mock_service.create_task.assert_called_once()

    def test_add_task_invalid_json_context(self) -> None:
        """Test adding a task with invalid JSON context fails."""
        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            result = runner.invoke(
                schedule.app,
                ["add", "echo hello", "60", "--context", "not valid json"],
            )

            assert result.exit_code == 1
            assert "Invalid JSON" in result.output


class TestScheduleListCommand:
    """Tests for schedule list command."""

    def test_list_no_tasks(self) -> None:
        """Test listing when no tasks exist."""
        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_pending_tasks.return_value = []
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["list"])

            assert result.exit_code == 0
            assert "No pending tasks" in result.output

    def test_list_with_tasks(self) -> None:
        """Test listing with pending tasks."""
        mock_task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="echo hello",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_pending_tasks.return_value = [mock_task]
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["list"])

            assert result.exit_code == 0
            assert "task-001" in result.output
            assert "echo hello" in result.output


class TestScheduleShowCommand:
    """Tests for schedule show command."""

    def test_show_task_success(self) -> None:
        """Test showing a task that exists."""
        mock_task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="echo hello",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
            context={"key": "value"},
        )

        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_task.return_value = mock_task
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["show", "task-001"])

            assert result.exit_code == 0
            assert "Task ID: task-001" in result.output
            assert "echo hello" in result.output
            assert "PENDING" in result.output

    def test_show_task_not_found(self) -> None:
        """Test showing a task that doesn't exist."""
        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_task.return_value = None
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["show", "nonexistent"])

            assert result.exit_code == 1
            assert "Task not found" in result.output


class TestScheduleCancelCommand:
    """Tests for schedule cancel command."""

    def test_cancel_task_success(self) -> None:
        """Test canceling a task that exists."""
        mock_task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="echo hello",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_task.return_value = mock_task
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["cancel", "task-001"])

            assert result.exit_code == 0
            assert "Cancelled task" in result.output
            mock_service.cancel_task.assert_called_once_with("task-001")

    def test_cancel_task_not_found(self) -> None:
        """Test canceling a task that doesn't exist."""
        with patch.object(schedule, "get_scheduler_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_task.return_value = None
            mock_get_service.return_value = mock_service

            result = runner.invoke(schedule.app, ["cancel", "nonexistent"])

            assert result.exit_code == 1
            assert "Task not found" in result.output
