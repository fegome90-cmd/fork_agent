"""Tests for ScheduledTask entity validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import pytest

from src.domain.entities.scheduled_task import ScheduledTask, TaskStatus


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self) -> None:
        """Test that TaskStatus has expected string values."""
        assert TaskStatus.PENDING.value == "PENDING"
        assert TaskStatus.EXECUTED.value == "EXECUTED"
        assert TaskStatus.CANCELLED.value == "CANCELLED"
        assert TaskStatus.FAILED.value == "FAILED"

    def test_task_status_from_string(self) -> None:
        """Test creating TaskStatus from string."""
        assert TaskStatus("PENDING") == TaskStatus.PENDING
        assert TaskStatus("EXECUTED") == TaskStatus.EXECUTED


class TestScheduledTaskValid:
    """Tests for valid ScheduledTask creation."""

    def test_create_scheduled_task_minimal(self) -> None:
        """Test creating a scheduled task with minimal fields."""
        task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="test_action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        assert task.id == "task-001"
        assert task.scheduled_at == 1234567890000
        assert task.action == "test_action"
        assert task.status == TaskStatus.PENDING
        assert task.created_at == 1234567890000
        assert task.context is None

    def test_create_scheduled_task_with_context(self) -> None:
        """Test creating a scheduled task with context."""
        context = {"key": "value", "number": 42}
        task = ScheduledTask(
            id="task-002",
            scheduled_at=1234567890000,
            action="test_action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
            context=context,
        )

        assert task.context == context

    def test_scheduled_task_is_frozen(self) -> None:
        """Test that ScheduledTask is immutable (frozen dataclass)."""
        task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="test_action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        with pytest.raises(FrozenInstanceError):
            task.id = "new-id"  # type: ignore[misc]


class TestScheduledTaskValidation:
    """Tests for ScheduledTask __post_init__ validation."""

    def test_invalid_id_type(self) -> None:
        """Test that non-string id raises TypeError."""
        with pytest.raises(TypeError, match="id debe ser un string"):
            ScheduledTask(
                id=123,  # type: ignore[arg-type]
                scheduled_at=1234567890000,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

    def test_empty_id(self) -> None:
        """Test that empty id raises ValueError."""
        with pytest.raises(ValueError, match="id no puede estar vacío"):
            ScheduledTask(
                id="",
                scheduled_at=1234567890000,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

    def test_invalid_scheduled_at_type(self) -> None:
        """Test that non-int scheduled_at raises TypeError."""
        with pytest.raises(TypeError, match="scheduled_at debe ser un entero"):
            ScheduledTask(
                id="task-001",
                scheduled_at="not an int",  # type: ignore[arg-type]
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

    def test_negative_scheduled_at(self) -> None:
        """Test that negative scheduled_at raises ValueError."""
        with pytest.raises(ValueError, match="scheduled_at debe ser no negativo"):
            ScheduledTask(
                id="task-001",
                scheduled_at=-1,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

    def test_invalid_action_type(self) -> None:
        """Test that non-string action raises TypeError."""
        with pytest.raises(TypeError, match="action debe ser un string"):
            ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action=123,  # type: ignore[arg-type]
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

    def test_empty_action(self) -> None:
        """Test that empty action raises ValueError."""
        with pytest.raises(ValueError, match="action no puede estar vacío"):
            ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action="",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

    def test_invalid_status_type(self) -> None:
        """Test that non-TaskStatus status raises TypeError."""
        with pytest.raises(TypeError, match="status debe ser un TaskStatus"):
            ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action="test_action",
                status="PENDING",  # type: ignore[arg-type]
                created_at=1234567890000,
            )

    def test_invalid_created_at_type(self) -> None:
        """Test that non-int created_at raises TypeError."""
        with pytest.raises(TypeError, match="created_at debe ser un entero"):
            ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at="not an int",  # type: ignore[arg-type]
            )

    def test_negative_created_at(self) -> None:
        """Test that negative created_at raises ValueError."""
        with pytest.raises(ValueError, match="created_at debe ser no negativo"):
            ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=-1,
            )

    def test_invalid_context_type(self) -> None:
        """Test that non-dict context raises TypeError."""
        with pytest.raises(TypeError, match="context debe ser un diccionario o None"):
            ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
                context="not a dict",  # type: ignore[arg-type]
            )
