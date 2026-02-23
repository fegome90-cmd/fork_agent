"""ScheduledTask repository for SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.application.exceptions import RepositoryError
from src.domain.entities.scheduled_task import ScheduledTask, TaskStatus
from src.infrastructure.persistence.database import DatabaseConnection


class ScheduledTaskRepository:
    """Repository for persisting and retrieving ScheduledTask entities."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def create(self, task: ScheduledTask) -> None:
        """Store a new scheduled task in the database.

        Args:
            task: The scheduled task entity to persist.

        Raises:
            RepositoryError: If the task ID already exists or database error occurs.
        """
        context_json = self._serialize_context(task.context)

        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT INTO scheduled_tasks (id, scheduled_at, action, context, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        task.id,
                        task.scheduled_at,
                        task.action,
                        context_json,
                        task.status.value,
                        task.created_at,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"ScheduledTask with id '{task.id}' already exists",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to create scheduled task: {e}", e) from e

    def get_by_id(self, task_id: str) -> ScheduledTask | None:
        """Retrieve a scheduled task by its ID.

        Args:
            task_id: The unique identifier of the scheduled task.

        Returns:
            The scheduled task entity if found, None otherwise.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT id, scheduled_at, action, context, status, created_at FROM scheduled_tasks WHERE id = ?",
                    (task_id,),
                )
                row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get scheduled task: {e}", e) from e

    def get_pending(self) -> list[ScheduledTask]:
        """Retrieve all pending scheduled tasks ordered by scheduled_at ascending.

        Returns:
            List of pending scheduled task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, scheduled_at, action, context, status, created_at
                       FROM scheduled_tasks
                       WHERE status = ?
                       ORDER BY scheduled_at ASC""",
                    (TaskStatus.PENDING.value,),
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get pending scheduled tasks: {e}", e) from e

    def get_overdue(self, current_time: int) -> list[ScheduledTask]:
        """Retrieve all overdue pending scheduled tasks.

        Args:
            current_time: Current Unix timestamp in milliseconds.

        Returns:
            List of overdue scheduled task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, scheduled_at, action, context, status, created_at
                       FROM scheduled_tasks
                       WHERE status = ? AND scheduled_at < ?
                       ORDER BY scheduled_at ASC""",
                    (TaskStatus.PENDING.value, current_time),
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get overdue scheduled tasks: {e}", e) from e

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Update the status of a scheduled task.

        Args:
            task_id: The unique identifier of the scheduled task.
            status: The new status to set.

        Raises:
            RepositoryError: If a database error occurs.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "UPDATE scheduled_tasks SET status = ? WHERE id = ?",
                    (status.value, task_id),
                )

                if cursor.rowcount == 0:
                    raise RepositoryError(f"ScheduledTask '{task_id}' not found")
        except RepositoryError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update scheduled task status: {e}", e) from e

    def delete(self, task_id: str) -> None:
        """Delete a scheduled task by its ID.

        Args:
            task_id: The unique identifier of the scheduled task to delete.

        Raises:
            RepositoryError: If a database error occurs.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "DELETE FROM scheduled_tasks WHERE id = ?",
                    (task_id,),
                )

                if cursor.rowcount == 0:
                    raise RepositoryError(f"ScheduledTask '{task_id}' not found")
        except RepositoryError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to delete scheduled task: {e}", e) from e

    def get_all(self) -> list[ScheduledTask]:
        """Retrieve all scheduled tasks ordered by created_at descending.

        Returns:
            List of all scheduled task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT id, scheduled_at, action, context, status, created_at FROM scheduled_tasks ORDER BY created_at DESC"
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get scheduled tasks: {e}", e) from e

    def _row_to_task(self, row: sqlite3.Row) -> ScheduledTask:
        """Convert a database row to a ScheduledTask entity."""
        context = self._deserialize_context(row["context"])
        return ScheduledTask(
            id=row["id"],
            scheduled_at=row["scheduled_at"],
            action=row["action"],
            context=context,
            status=TaskStatus(row["status"]),
            created_at=row["created_at"],
        )

    def _serialize_context(self, context: dict[str, Any] | None) -> str | None:
        """Serialize context dict to JSON string."""
        return json.dumps(context) if context is not None else None

    def _deserialize_context(self, context_json: str | None) -> dict[str, Any] | None:
        """Deserialize JSON string to context dict."""
        return json.loads(context_json) if context_json is not None else None
