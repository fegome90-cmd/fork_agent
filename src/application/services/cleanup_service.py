"""Cleanup service for managing old observations."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

from src.infrastructure.persistence.database import DatabaseConnection


@dataclass(frozen=True)
class CleanupResult:
    """Result of a cleanup operation."""

    deleted_count: int
    fts_deleted_count: int


class CleanupService:
    """Service for cleaning up old observations and maintaining database."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def cleanup_old_observations(self, days: int = 90, dry_run: bool = False) -> CleanupResult:
        """Delete observations older than specified days.

        Args:
            days: Number of days to keep. Default is 90.
            dry_run: If True, only count records without deleting.

        Returns:
            CleanupResult with counts of deleted records.
        """
        cutoff_timestamp = self._calculate_cutoff_timestamp(days)

        if dry_run:
            return self._count_old_observations(cutoff_timestamp)

        return self._delete_old_observations(cutoff_timestamp)

    def vacuum_database(self) -> None:
        """Run VACUUM to reclaim disk space after deletions."""
        try:
            with self._connection as conn:
                conn.execute("VACUUM")
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to vacuum database: {e}") from e

    def optimize_fts(self) -> None:
        """Optimize FTS5 index after bulk operations."""
        try:
            with self._connection as conn:
                conn.execute("INSERT INTO observations_fts(observations_fts) VALUES('optimize')")
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to optimize FTS: {e}") from e

    def _calculate_cutoff_timestamp(self, days: int) -> int:
        """Calculate the cutoff timestamp for deletion."""
        return int((time.time() - (days * 86400)) * 1000)

    def _count_old_observations(self, cutoff_timestamp: int) -> CleanupResult:
        """Count old observations without deleting."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM observations WHERE timestamp < ?",
                    (cutoff_timestamp,),
                )
                deleted_count = cursor.fetchone()[0]

                fts_cursor = conn.execute(
                    """SELECT COUNT(*) FROM observations o
                       WHERE o.timestamp < ?
                       AND EXISTS (SELECT 1 FROM observations_fts fts WHERE fts.rowid = o.rowid)""",
                    (cutoff_timestamp,),
                )
                fts_deleted_count = fts_cursor.fetchone()[0]

            return CleanupResult(deleted_count=deleted_count, fts_deleted_count=fts_deleted_count)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to count old observations: {e}") from e

    def _delete_old_observations(self, cutoff_timestamp: int) -> CleanupResult:
        """Delete old observations from both observations and FTS tables."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "DELETE FROM observations WHERE timestamp < ?",
                    (cutoff_timestamp,),
                )
                deleted_count = cursor.rowcount

                fts_cursor = conn.execute(
                    """DELETE FROM observations_fts
                       WHERE rowid IN (SELECT rowid FROM observations WHERE timestamp < ?)""",
                    (cutoff_timestamp,),
                )
                fts_deleted_count = fts_cursor.rowcount

            return CleanupResult(deleted_count=deleted_count, fts_deleted_count=fts_deleted_count)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to delete old observations: {e}") from e
