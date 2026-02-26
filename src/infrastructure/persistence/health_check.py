"""Health check service for database diagnostics."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.infrastructure.persistence.database import DatabaseConnection


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a health check."""

    is_healthy: bool
    integrity_ok: bool
    fts_synced: bool
    observation_count: int
    fts_count: int
    db_size_bytes: int
    issues: list[str]


class HealthCheckService:
    """Service for checking database health."""

    __slots__ = ("_connection", "_db_path")

    def __init__(self, connection: DatabaseConnection, db_path: Path | None = None) -> None:
        self._connection = connection
        self._db_path = db_path or Path("data/memory.db")

    def check_health(self, verbose: bool = False) -> HealthCheckResult:
        """Run full health check on the database.

        Args:
            verbose: Include detailed information in results.

        Returns:
            HealthCheckResult with health status and details.
        """
        _ = verbose  # Reserved for future detailed diagnostics
        issues: list[str] = []

        # Check integrity
        integrity_ok = self._check_integrity()

        # Check FTS sync
        fts_synced, obs_count, fts_count = self._check_fts_sync()

        if not integrity_ok:
            issues.append("Database integrity check failed")

        if not fts_synced:
            issues.append(f"FTS desync: {obs_count} observations but {fts_count} FTS entries")

        # Get DB size
        db_size = self._get_db_size()

        is_healthy = len(issues) == 0

        return HealthCheckResult(
            is_healthy=is_healthy,
            integrity_ok=integrity_ok,
            fts_synced=fts_synced,
            observation_count=obs_count,
            fts_count=fts_count,
            db_size_bytes=db_size,
            issues=issues,
        )

    def get_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with database statistics.
        """
        _, obs_count, fts_count = self._check_fts_sync()

        return {
            "observation_count": obs_count,
            "fts_count": fts_count,
            "db_size_bytes": self._get_db_size(),
            "db_size_human": self._format_bytes(self._get_db_size()),
        }

    def repair_fts(self) -> int:
        """Repair FTS index by rebuilding from observations table.

        Returns:
            Number of entries rebuilt.
        """
        try:
            with self._connection as conn:
                # Get all observations
                cursor = conn.execute("SELECT rowid, content FROM observations")
                observations = cursor.fetchall()

                # Delete all FTS entries
                conn.execute("DELETE FROM observations_fts")

                # Reinsert all observations
                for obs in observations:
                    conn.execute(
                        "INSERT INTO observations_fts(rowid, content) VALUES (?, ?)",
                        (obs[0], obs[1]),
                    )

                return len(observations)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to repair FTS: {e}") from e

    def _check_integrity(self) -> bool:
        """Check database integrity."""
        try:
            with self._connection as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                return result[0] == "ok"
        except sqlite3.Error:
            return False

    def _check_fts_sync(self) -> tuple[bool, int, int]:
        """Check if FTS index is synced with observations table."""
        try:
            with self._connection as conn:
                obs_cursor = conn.execute("SELECT COUNT(*) FROM observations")
                obs_count = obs_cursor.fetchone()[0]

                fts_cursor = conn.execute("SELECT COUNT(*) FROM observations_fts")
                fts_count = fts_cursor.fetchone()[0]

                return obs_count == fts_count, obs_count, fts_count
        except sqlite3.Error:
            return False, 0, 0

    def _get_db_size(self) -> int:
        """Get database file size in bytes."""
        try:
            return self._db_path.stat().st_size if self._db_path.exists() else 0
        except OSError:
            return 0

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
