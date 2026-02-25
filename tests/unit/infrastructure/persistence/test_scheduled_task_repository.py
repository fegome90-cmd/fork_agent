"""Unit tests for ScheduledTaskRepository."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from src.application.exceptions import RepositoryError
from src.domain.entities.scheduled_task import ScheduledTask, TaskStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.scheduled_task_repository import (
    ScheduledTaskRepository,
)


@pytest.fixture
def db_connection() -> DatabaseConnection:
    """Create a temporary in-memory database with schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config = DatabaseConfig(db_path=db_path)
        conn = DatabaseConnection(config)

        with conn as c:
            c.execute(
                """CREATE TABLE scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    scheduled_at INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    context TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at INTEGER NOT NULL
                )"""
            )

        yield conn


@pytest.fixture
def repository(db_connection: DatabaseConnection) -> ScheduledTaskRepository:
    """Create repository with test database."""
    return ScheduledTaskRepository(db_connection)


class TestScheduledTaskRepositoryCreate:
    """Tests for create method."""

    def test_create_task_success(self, repository: ScheduledTaskRepository) -> None:
        """Test successful task creation."""
        task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="test_action",
            context={"key": "value"},
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        repository.create(task)

        retrieved = repository.get_by_id("task-001")
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.action == task.action

    def test_create_task_with_null_context(self, repository: ScheduledTaskRepository) -> None:
        """Test task creation with null context."""
        task = ScheduledTask(
            id="task-002",
            scheduled_at=1234567890000,
            action="simple_action",
            context=None,
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        repository.create(task)

        retrieved = repository.get_by_id("task-002")
        assert retrieved is not None
        assert retrieved.context is None

    def test_create_duplicate_id_raises_error(self, repository: ScheduledTaskRepository) -> None:
        """Test that duplicate ID raises RepositoryError."""
        task = ScheduledTask(
            id="task-duplicate",
            scheduled_at=1234567890000,
            action="action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )

        repository.create(task)

        with pytest.raises(RepositoryError, match="already exists"):
            repository.create(task)


class TestScheduledTaskRepositoryGetById:
    """Tests for get_by_id method."""

    def test_get_existing_task(self, repository: ScheduledTaskRepository) -> None:
        """Test getting an existing task."""
        task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="test_action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )
        repository.create(task)

        retrieved = repository.get_by_id("task-001")

        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.action == task.action

    def test_get_non_existing_task(self, repository: ScheduledTaskRepository) -> None:
        """Test getting a non-existent task returns None."""
        retrieved = repository.get_by_id("non-existent")
        assert retrieved is None


class TestScheduledTaskRepositoryGetPending:
    """Tests for get_pending method."""

    def test_get_pending_tasks(self, repository: ScheduledTaskRepository) -> None:
        """Test getting all pending tasks."""
        task1 = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="action1",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )
        task2 = ScheduledTask(
            id="task-002",
            scheduled_at=1234567891000,
            action="action2",
            status=TaskStatus.PENDING,
            created_at=1234567891000,
        )
        task3 = ScheduledTask(
            id="task-003",
            scheduled_at=1234567892000,
            action="action3",
            status=TaskStatus.EXECUTED,
            created_at=1234567892000,
        )

        repository.create(task1)
        repository.create(task2)
        repository.create(task3)

        pending = repository.get_pending()

        assert len(pending) == 2
        assert all(t.status == TaskStatus.PENDING for t in pending)


class TestScheduledTaskRepositoryGetOverdue:
    """Tests for get_overdue method."""

    def test_get_overdue_tasks(self, repository: ScheduledTaskRepository) -> None:
        """Test getting overdue pending tasks."""
        current_time = int(time.time() * 1000)

        task1 = ScheduledTask(
            id="overdue-task",
            scheduled_at=current_time - 60000,
            action="overdue_action",
            status=TaskStatus.PENDING,
            created_at=current_time - 120000,
        )
        task2 = ScheduledTask(
            id="future-task",
            scheduled_at=current_time + 60000,
            action="future_action",
            status=TaskStatus.PENDING,
            created_at=current_time - 60000,
        )

        repository.create(task1)
        repository.create(task2)

        overdue = repository.get_overdue(current_time)

        assert len(overdue) == 1
        assert overdue[0].id == "overdue-task"


class TestScheduledTaskRepositoryUpdateStatus:
    """Tests for update_status method."""

    def test_update_status_success(self, repository: ScheduledTaskRepository) -> None:
        """Test successful status update."""
        task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )
        repository.create(task)

        repository.update_status("task-001", TaskStatus.EXECUTED)

        updated = repository.get_by_id("task-001")
        assert updated is not None
        assert updated.status == TaskStatus.EXECUTED

    def test_update_status_nonexistent_raises_error(
        self, repository: ScheduledTaskRepository
    ) -> None:
        """Test updating nonexistent task raises error."""
        with pytest.raises(RepositoryError, match="not found"):
            repository.update_status("non-existent", TaskStatus.EXECUTED)


class TestScheduledTaskRepositoryDelete:
    """Tests for delete method."""

    def test_delete_existing_task(self, repository: ScheduledTaskRepository) -> None:
        """Test deleting an existing task."""
        task = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="action",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )
        repository.create(task)

        repository.delete("task-001")

        assert repository.get_by_id("task-001") is None

    def test_delete_nonexistent_raises_error(self, repository: ScheduledTaskRepository) -> None:
        """Test deleting nonexistent task raises error."""
        with pytest.raises(RepositoryError, match="not found"):
            repository.delete("non-existent")


class TestScheduledTaskRepositoryGetAll:
    """Tests for get_all method."""

    def test_get_all_tasks(self, repository: ScheduledTaskRepository) -> None:
        """Test getting all tasks."""
        task1 = ScheduledTask(
            id="task-001",
            scheduled_at=1234567890000,
            action="action1",
            status=TaskStatus.PENDING,
            created_at=1234567890000,
        )
        task2 = ScheduledTask(
            id="task-002",
            scheduled_at=1234567891000,
            action="action2",
            status=TaskStatus.EXECUTED,
            created_at=1234567891000,
        )

        repository.create(task1)
        repository.create(task2)

        all_tasks = repository.get_all()

        assert len(all_tasks) == 2


class TestScheduledTaskRepositoryErrorHandling:
    """Tests for error handling in ScheduledTaskRepository."""

    def test_create_database_error(self) -> None:
        """Test that database error in create raises RepositoryError."""
        # Use a path that will fail
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "readonly" / "test.db"
            # Don't create parent directory - this will cause an error
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            task = ScheduledTask(
                id="task-001",
                scheduled_at=1234567890000,
                action="test_action",
                status=TaskStatus.PENDING,
                created_at=1234567890000,
            )

            with pytest.raises(RepositoryError, match="Failed to create"):
                repository.create(task)

    def test_get_by_id_database_error(self) -> None:
        """Test that database error in get_by_id raises RepositoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent" / "test.db"
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            with pytest.raises(RepositoryError, match="Failed to get"):
                repository.get_by_id("task-001")

    def test_get_pending_database_error(self) -> None:
        """Test that database error in get_pending raises RepositoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent" / "test.db"
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            with pytest.raises(RepositoryError, match="Failed to get pending"):
                repository.get_pending()

    def test_get_overdue_database_error(self) -> None:
        """Test that database error in get_overdue raises RepositoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent" / "test.db"
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            with pytest.raises(RepositoryError, match="Failed to get overdue"):
                repository.get_overdue(1234567890000)

    def test_update_status_database_error(self) -> None:
        """Test that database error in update_status raises RepositoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent" / "test.db"
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            with pytest.raises(RepositoryError, match="Failed to update"):
                repository.update_status("task-001", TaskStatus.EXECUTED)

    def test_delete_database_error(self) -> None:
        """Test that database error in delete raises RepositoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent" / "test.db"
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            with pytest.raises(RepositoryError, match="Failed to delete"):
                repository.delete("task-001")

    def test_get_all_database_error(self) -> None:
        """Test that database error in get_all raises RepositoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent" / "test.db"
            config = DatabaseConfig(db_path=db_path)
            conn = DatabaseConnection(config)
            repository = ScheduledTaskRepository(conn)

            with pytest.raises(RepositoryError, match="Failed to get"):
                repository.get_all()
