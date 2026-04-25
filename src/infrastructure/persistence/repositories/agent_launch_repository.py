"""SQLite agent launch registry — canonical ownership and CAS transitions."""

from __future__ import annotations

import logging
import sqlite3
import time

from src.application.exceptions import RepositoryError
from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus
from src.infrastructure.persistence.database import DatabaseConnection

logger = logging.getLogger(__name__)


class SqliteAgentLaunchRepository:
    """SQLite-backed launch registry with atomic claim and CAS status updates."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def claim(
        self,
        launch_id: str,
        canonical_key: str,
        surface: str,
        owner_type: str,
        owner_id: str,
        lease_expires_at: int,
    ) -> AgentLaunch | None:
        """Atomically claim a RESERVED launch slot.

        Uses the partial unique index idx_one_active_launch_per_key to prevent
        duplicate active claims for the same canonical key. If the INSERT would
        violate the constraint, returns None (no exception).
        """
        now_ms = int(time.time() * 1000)
        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT INTO agent_launch_registry
                       (launch_id, canonical_key, surface, owner_type, owner_id,
                        status, created_at, reserved_at, lease_expires_at)
                       VALUES (?, ?, ?, ?, ?, 'RESERVED', ?, ?, ?)""",
                    (launch_id, canonical_key, surface, owner_type, owner_id, now_ms, now_ms, lease_expires_at),
                )
            logger.info(
                "Claimed launch %s for canonical_key=%s surface=%s",
                launch_id,
                canonical_key,
                surface,
            )
            return self.get_by_launch_id(launch_id)
        except sqlite3.IntegrityError as e:
            err_msg = str(e)
            # Only suppress duplicate-key violations from the partial unique index.
            # Other IntegrityErrors (e.g., NOT NULL violations) indicate schema bugs
            # and must NOT be silently suppressed.
            if "unique" in err_msg.lower() or "idx_one_active_launch_per_key" in err_msg:
                logger.info(
                    "Claim rejected for canonical_key=%s: blocking launch already active",
                    canonical_key,
                )
                return None
            raise RepositoryError(
                f"Unexpected IntegrityError during claim: {e}", e
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to claim launch: {e}", e) from e

    def get_by_launch_id(self, launch_id: str) -> AgentLaunch | None:
        """Retrieve a launch record by its stable launch_id."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT * FROM agent_launch_registry WHERE launch_id = ?",
                    (launch_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_launch(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get launch: {e}", e) from e

    def find_active_by_canonical_key(self, canonical_key: str) -> AgentLaunch | None:
        """Find the active (blocking) launch for a canonical key."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT * FROM agent_launch_registry
                       WHERE canonical_key = ?
                         AND status IN ('RESERVED', 'SPAWNING', 'ACTIVE', 'TERMINATING')
                       ORDER BY created_at DESC LIMIT 1""",
                    (canonical_key,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_launch(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to find active launch: {e}", e) from e

    def cas_update_status(
        self,
        launch_id: str,
        expected_status: LaunchStatus,
        new_status: LaunchStatus,
        *,
        error: str | None = None,
        quarantine_reason: str | None = None,
        backend: str | None = None,
        termination_handle_type: str | None = None,
        termination_handle_value: str | None = None,
        process_pid: int | None = None,
        process_pgid: int | None = None,
        tmux_session: str | None = None,
        tmux_pane_id: str | None = None,
    ) -> bool:
        """CAS update — only succeeds if current status matches expected_status.

        Uses a fully static SQL statement with COALESCE to preserve existing
        column values when optional parameters are None. No dynamic SQL construction.

        Note: COALESCE(?, column) means passing NULL will NOT clear an existing
        value. To explicitly clear a field, a separate UPDATE statement is needed.
        """
        is_terminal = new_status in (
            LaunchStatus.TERMINATED,
            LaunchStatus.FAILED,
            LaunchStatus.SUPPRESSED_DUPLICATE,
        )
        ended_at_val = int(time.time() * 1000) if is_terminal else None
        spawn_started_at_val = int(time.time() * 1000) if new_status == LaunchStatus.SPAWNING else None
        spawn_confirmed_at_val = int(time.time() * 1000) if new_status == LaunchStatus.ACTIVE else None

        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """UPDATE agent_launch_registry SET
                        status = ?,
                        ended_at = COALESCE(?, ended_at),
                        spawn_started_at = COALESCE(?, spawn_started_at),
                        spawn_confirmed_at = COALESCE(?, spawn_confirmed_at),
                        last_error = COALESCE(?, last_error),
                        quarantine_reason = COALESCE(?, quarantine_reason),
                        backend = COALESCE(?, backend),
                        termination_handle_type = COALESCE(?, termination_handle_type),
                        termination_handle_value = COALESCE(?, termination_handle_value),
                        process_pid = COALESCE(?, process_pid),
                        process_pgid = COALESCE(?, process_pgid),
                        tmux_session = COALESCE(?, tmux_session),
                        tmux_pane_id = COALESCE(?, tmux_pane_id)
                       WHERE launch_id = ? AND status = ?""",
                    (
                        new_status.value,
                        ended_at_val,
                        spawn_started_at_val,
                        spawn_confirmed_at_val,
                        error,
                        quarantine_reason,
                        backend,
                        termination_handle_type,
                        termination_handle_value,
                        process_pid,
                        process_pgid,
                        tmux_session,
                        tmux_pane_id,
                        launch_id,
                        expected_status.value,
                    ),
                )
                updated = cursor.rowcount > 0

            if updated:
                logger.info(
                    "CAS status %s -> %s for launch %s",
                    expected_status.value,
                    new_status.value,
                    launch_id,
                )
            else:
                logger.debug(
                    "CAS failed for launch %s: expected %s but status didn't match",
                    launch_id,
                    expected_status.value,
                )
            return updated
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to CAS update launch: {e}", e) from e

    def list_by_status(self, status: LaunchStatus) -> list[AgentLaunch]:
        """List all launches in a given status."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT * FROM agent_launch_registry WHERE status = ? ORDER BY created_at DESC",
                    (status.value,),
                )
                return [self._row_to_launch(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list launches by status: {e}", e) from e

    def list_expired_leases(self, now_ms: int) -> list[AgentLaunch]:
        """Find launches with expired leases still in pre-spawn states."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT * FROM agent_launch_registry
                       WHERE status IN ('RESERVED', 'SPAWNING')
                         AND lease_expires_at IS NOT NULL
                         AND lease_expires_at <= ?
                       ORDER BY lease_expires_at ASC""",
                    (now_ms,),
                )
                return [self._row_to_launch(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list expired leases: {e}", e) from e

    def count_by_status(self) -> dict[str, int]:
        """Return counts grouped by status."""
        try:
            with self._connection as conn:
                rows = conn.execute(
                    "SELECT status, COUNT(*) as cnt FROM agent_launch_registry GROUP BY status"
                ).fetchall()
                return {row["status"]: row["cnt"] for row in rows}
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to count launches by status: {e}", e) from e

    @staticmethod
    def _row_to_launch(row: sqlite3.Row) -> AgentLaunch:
        """Convert a database row to an AgentLaunch entity."""
        try:
            status = LaunchStatus(row["status"])
        except ValueError as e:
            raise RepositoryError(
                f"Invalid status '{row['status']}' for launch '{row['launch_id']}'"
            ) from e
        return AgentLaunch(
            launch_id=row["launch_id"],
            canonical_key=row["canonical_key"],
            surface=row["surface"],
            owner_type=row["owner_type"],
            owner_id=row["owner_id"],
            status=status,
            backend=row["backend"],
            created_at=row["created_at"],
            reserved_at=row["reserved_at"],
            spawn_started_at=row["spawn_started_at"],
            spawn_confirmed_at=row["spawn_confirmed_at"],
            ended_at=row["ended_at"],
            lease_expires_at=row["lease_expires_at"],
            termination_handle_type=row["termination_handle_type"],
            termination_handle_value=row["termination_handle_value"],
            process_pid=row["process_pid"],
            process_pgid=row["process_pgid"],
            tmux_session=row["tmux_session"],
            tmux_pane_id=row["tmux_pane_id"],
            prompt_digest=row["prompt_digest"],
            request_fingerprint=row["request_fingerprint"],
            last_error=row["last_error"],
            quarantine_reason=row["quarantine_reason"],
        )
