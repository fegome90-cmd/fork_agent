"""Poll run repository for SQLite persistence."""

from __future__ import annotations

import sqlite3
import time

from src.application.exceptions import RepositoryError
from src.domain.entities.poll_run import PollRun, PollRunStatus
from src.infrastructure.persistence.database import DatabaseConnection


class SqlitePollRunRepository:
    """Repository for persisting and retrieving PollRun entities."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def save(self, run: PollRun) -> None:
        """Persist a poll run (insert or replace)."""
        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO poll_runs
                       (id, task_id, agent_name, status, started_at, ended_at, poll_run_dir, error_message)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run.id,
                        run.task_id,
                        run.agent_name,
                        run.status.value,
                        run.started_at,
                        run.ended_at,
                        run.poll_run_dir,
                        run.error_message,
                    ),
                )
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save poll run: {e}", e) from e

    def get_by_id(self, run_id: str) -> PollRun | None:
        """Retrieve a poll run by its ID."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, task_id, agent_name, status, started_at,
                              ended_at, poll_run_dir, error_message
                       FROM poll_runs WHERE id = ?""",
                    (run_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_run(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get poll run: {e}", e) from e

    def list_by_status(self, status: PollRunStatus) -> list[PollRun]:
        """Retrieve all poll runs with a given status."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, task_id, agent_name, status, started_at,
                              ended_at, poll_run_dir, error_message
                       FROM poll_runs WHERE status = ?
                       ORDER BY started_at DESC""",
                    (status.value,),
                )
                return [self._row_to_run(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list poll runs by status: {e}", e) from e

    def list_active(self) -> list[PollRun]:
        """Retrieve all active (QUEUED or RUNNING) poll runs."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, task_id, agent_name, status, started_at,
                              ended_at, poll_run_dir, error_message
                       FROM poll_runs
                       WHERE status IN ('QUEUED', 'RUNNING')
                       ORDER BY started_at DESC""",
                )
                return [self._row_to_run(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list active poll runs: {e}", e) from e

    # TODO: migrate all callers to cas_update_status
    def update_status(
        self, run_id: str, status: PollRunStatus, error_message: str | None = None
    ) -> None:
        """Update a poll run's status (no CAS guard — deprecated).

        Terminal statuses (COMPLETED, FAILED, CANCELLED) also set ended_at.
        Non-terminal statuses set started_at.
        """
        now_ms = int(time.time() * 1000)
        try:
            with self._connection as conn:
                if status in (
                    PollRunStatus.COMPLETED,
                    PollRunStatus.FAILED,
                    PollRunStatus.CANCELLED,
                ):
                    conn.execute(
                        """UPDATE poll_runs SET status = ?, ended_at = ?, error_message = ?
                            WHERE id = ?""",
                        (status.value, now_ms, error_message, run_id),
                    )
                else:
                    conn.execute(
                        "UPDATE poll_runs SET status = ?, started_at = ? WHERE id = ?",
                        (status.value, now_ms, run_id),
                    )
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update poll run status: {e}", e) from e

    def cas_update_status(
        self,
        run_id: str,
        expected_status: PollRunStatus,
        new_status: PollRunStatus,
        error_message: str | None = None,
        started_at: int | None = None,
    ) -> bool:
        """CAS update — only succeeds if current status matches expected_status.

        Returns True if the row was updated, False if the CAS guard failed.
        """
        now_ms = int(time.time() * 1000)
        started_at_val = started_at if started_at is not None else now_ms
        try:
            with self._connection as conn:
                if new_status in (
                    PollRunStatus.COMPLETED,
                    PollRunStatus.FAILED,
                    PollRunStatus.CANCELLED,
                ):
                    cursor = conn.execute(
                        """UPDATE poll_runs SET status = ?, ended_at = ?, error_message = ?, started_at = ?
                            WHERE id = ? AND status = ?""",
                        (
                            new_status.value,
                            now_ms,
                            error_message,
                            started_at_val,
                            run_id,
                            expected_status.value,
                        ),
                    )
                else:
                    cursor = conn.execute(
                        "UPDATE poll_runs SET status = ?, started_at = ? WHERE id = ? AND status = ?",
                        (new_status.value, started_at_val, run_id, expected_status.value),
                    )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to CAS update poll run status: {e}", e) from e

    def count_by_status(self) -> dict[str, int]:
        """Return counts grouped by status — single query."""
        try:
            with self._connection as conn:
                rows = conn.execute(
                    "SELECT status, COUNT(*) as cnt FROM poll_runs GROUP BY status"
                ).fetchall()
                return {row["status"]: row["cnt"] for row in rows}
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to count poll runs by status: {e}", e) from e

    def remove(self, run_id: str) -> None:
        """Hard-delete a poll run."""
        try:
            with self._connection as conn:
                conn.execute("DELETE FROM poll_runs WHERE id = ?", (run_id,))
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to remove poll run: {e}", e) from e

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> PollRun:
        """Convert a database row to a PollRun entity."""
        try:
            status = PollRunStatus(row["status"])
        except ValueError as e:
            raise RepositoryError(
                f"Invalid status '{row['status']}' for poll run '{row['id']}'"
            ) from e
        return PollRun(
            id=row["id"],
            task_id=row["task_id"],
            agent_name=row["agent_name"],
            status=status,
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            poll_run_dir=row["poll_run_dir"],
            error_message=row["error_message"],
        )
