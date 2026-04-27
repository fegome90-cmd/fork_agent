"""OrchestrationTask repository for SQLite persistence."""

from __future__ import annotations

import json
import sqlite3

from src.application.exceptions import RepositoryError
from src.domain.entities.orchestration_task import OrchestrationTask, OrchestrationTaskStatus
from src.infrastructure.persistence.database import DatabaseConnection


class SqliteOrchestrationTaskRepository:
    """Repository for persisting and retrieving OrchestrationTask entities."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def save(self, task: OrchestrationTask) -> None:
        """Persist an orchestration task (insert or replace).

        Args:
            task: The orchestration task entity to persist.

        Raises:
            RepositoryError: If a database error occurs.
        """
        blocked_by_json = json.dumps(list(task.blocked_by))

        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO orchestration_tasks
                       (id, subject, description, status, owner, blocked_by,
                        plan_text, created_at, updated_at, approved_by, approved_at,
                        requested_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task.id,
                        task.subject,
                        task.description,
                        task.status.value,
                        task.owner,
                        blocked_by_json,
                        task.plan_text,
                        task.created_at,
                        task.updated_at,
                        task.approved_by,
                        task.approved_at,
                        task.requested_by,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"OrchestrationTask with id '{task.id}' constraint violation",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save orchestration task: {e}", e) from e

    def cas_save(self, task: OrchestrationTask, expected_status: OrchestrationTaskStatus) -> bool:
        """Compare-and-save: update *task* only if the DB row's status still matches.

        Uses ``UPDATE ... WHERE id = ? AND status = ?`` so that a concurrent
        writer who already changed the status causes the update to affect zero
        rows.

        Returns:
            True if the row was updated, False if the status guard failed.
        """
        blocked_by_json = json.dumps(list(task.blocked_by))
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """UPDATE orchestration_tasks
                       SET subject = ?, description = ?, status = ?, owner = ?,
                           blocked_by = ?, plan_text = ?, created_at = ?,
                           updated_at = ?, approved_by = ?, approved_at = ?,
                           requested_by = ?
                       WHERE id = ? AND status = ?""",
                    (
                        task.subject,
                        task.description,
                        task.status.value,
                        task.owner,
                        blocked_by_json,
                        task.plan_text,
                        task.created_at,
                        task.updated_at,
                        task.approved_by,
                        task.approved_at,
                        task.requested_by,
                        task.id,
                        expected_status.value,
                    ),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to cas_save orchestration task: {e}", e) from e

    def get_by_id(self, task_id: str) -> OrchestrationTask | None:
        """Retrieve an orchestration task by its ID.

        Args:
            task_id: The unique identifier of the task.

        Returns:
            The orchestration task entity if found, None otherwise.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, subject, description, status, owner, blocked_by,
                              plan_text, created_at, updated_at, approved_by, approved_at,
                              requested_by
                       FROM orchestration_tasks WHERE id = ?""",
                    (task_id,),
                )
                row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get orchestration task: {e}", e) from e

    def get_by_ids(self, task_ids: list[str]) -> list[OrchestrationTask]:
        """Retrieve multiple tasks by their IDs in a single query.

        Returns an empty list if *task_ids* is empty.  The order of results
        is not guaranteed.
        """
        if not task_ids:
            return []
        try:
            placeholders = ", ".join("?" for _ in task_ids)
            with self._connection as conn:
                cursor = conn.execute(
                    f"""SELECT id, subject, description, status, owner, blocked_by,
                               plan_text, created_at, updated_at, approved_by, approved_at,
                               requested_by
                        FROM orchestration_tasks WHERE id IN ({placeholders})""",
                    task_ids,
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get orchestration tasks by ids: {e}", e) from e

    def list_by_status(self, status: OrchestrationTaskStatus) -> list[OrchestrationTask]:
        """Retrieve all orchestration tasks with a given status.

        Args:
            status: The status to filter by.

        Returns:
            List of matching orchestration task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, subject, description, status, owner, blocked_by,
                              plan_text, created_at, updated_at, approved_by, approved_at,
                              requested_by
                       FROM orchestration_tasks
                       WHERE status = ?
                       ORDER BY created_at DESC""",
                    (status.value,),
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list orchestration tasks by status: {e}", e) from e

    def list_by_owner(self, owner: str) -> list[OrchestrationTask]:
        """Retrieve all orchestration tasks assigned to a given owner.

        Args:
            owner: The owner identifier to filter by.

        Returns:
            List of matching orchestration task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, subject, description, status, owner, blocked_by,
                              plan_text, created_at, updated_at, approved_by, approved_at,
                              requested_by
                       FROM orchestration_tasks
                       WHERE owner = ?
                       ORDER BY created_at DESC""",
                    (owner,),
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list orchestration tasks by owner: {e}", e) from e

    def list_all(self) -> list[OrchestrationTask]:
        """Retrieve all orchestration tasks ordered by creation time.

        Returns:
            List of all orchestration task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, subject, description, status, owner, blocked_by,
                              plan_text, created_at, updated_at, approved_by, approved_at,
                              requested_by
                       FROM orchestration_tasks
                       ORDER BY created_at DESC""",
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list all orchestration tasks: {e}") from e

    def list_blocked(self) -> list[OrchestrationTask]:
        """Retrieve all orchestration tasks that have non-empty blocked_by.

        Returns:
            List of blocked orchestration task entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, subject, description, status, owner, blocked_by,
                              plan_text, created_at, updated_at, approved_by, approved_at,
                              requested_by
                       FROM orchestration_tasks
                       WHERE blocked_by != '[]'
                       ORDER BY created_at DESC""",
                )
                rows = cursor.fetchall()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list blocked orchestration tasks: {e}", e) from e

    def remove(self, task_id: str) -> None:
        """Hard-delete an orchestration task by its ID.

        Args:
            task_id: The unique identifier of the task to delete.

        Raises:
            RepositoryError: If the task is not found or a database error occurs.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "DELETE FROM orchestration_tasks WHERE id = ?",
                    (task_id,),
                )

                if cursor.rowcount == 0:
                    raise RepositoryError(f"OrchestrationTask '{task_id}' not found")
        except RepositoryError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to remove orchestration task: {e}", e) from e

    def _row_to_task(self, row: sqlite3.Row) -> OrchestrationTask:
        """Convert a database row to an OrchestrationTask entity."""
        blocked_by = self._deserialize_blocked_by(row["blocked_by"])
        try:
            status = OrchestrationTaskStatus(row["status"])
        except ValueError:
            raise RepositoryError(
                f"Invalid status '{row['status']}' in database for task '{row['id']}'"
            ) from None
        return OrchestrationTask(
            id=row["id"],
            subject=row["subject"],
            description=row["description"],
            status=status,
            owner=row["owner"],
            blocked_by=blocked_by,
            plan_text=row["plan_text"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            requested_by=row["requested_by"],
        )

    @staticmethod
    def _deserialize_blocked_by(value: str | None) -> tuple[str, ...]:
        """Deserialize a JSON array string into a tuple of task IDs.

        Returns an empty tuple if the value is None, empty, or contains
        malformed JSON (defensive against corrupt database rows).
        """
        if value is None or value == "[]":
            return ()
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return ()
        if not isinstance(parsed, list):
            return ()
        return tuple(str(item) for item in parsed)
