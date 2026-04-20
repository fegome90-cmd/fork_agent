"""Telemetry repository implementation for SQLite persistence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import types
import uuid
from datetime import UTC, datetime
from typing import Any

from src.domain.entities.telemetry_event import (
    MetricBucket,
    SessionSummary,
    TelemetryEvent,
)
from src.domain.ports.telemetry_repository import TelemetryRepository
from src.infrastructure.persistence.database import DatabaseConnection


class TelemetryRepositoryImpl(TelemetryRepository):
    """SQLite implementation of the telemetry repository."""

    __slots__ = ("_connection", "_tables_verified")

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection
        self._tables_verified = False
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure all required tables exist. Cached after first check."""
        if self._tables_verified:
            return

        # Tables are created via migrations, but we ensure they're accessible
        with self._connection as conn:
            # Verify tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ("
                "'telemetry_events', 'telemetry_metrics', 'telemetry_sessions')"
            )
            tables = {row[0] for row in cursor.fetchall()}
            if "telemetry_events" not in tables:
                raise RuntimeError("telemetry_events table not found. Run migrations first.")
            if "telemetry_metrics" not in tables:
                raise RuntimeError("telemetry_metrics table not found. Run migrations first.")
            if "telemetry_sessions" not in tables:
                raise RuntimeError("telemetry_sessions table not found. Run migrations first.")

        self._tables_verified = True

    def _serialize_attributes(self, attributes: dict[str, Any]) -> str:
        return json.dumps(dict(attributes))

    def _deserialize_attributes(self, data: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(data, str):
            return json.loads(data)  # type: ignore[no-any-return]
        return data

    def _serialize_metrics(self, metrics: dict[str, Any] | None) -> str | None:
        if metrics is None:
            return None
        return json.dumps(dict(metrics))

    def _deserialize_metrics(self, data: str | dict[str, Any] | None) -> dict[str, Any] | None:
        if data is None:
            return None
        if isinstance(data, str):
            return json.loads(data)  # type: ignore[no-any-return]
        return data

    def _get_optional(self, row: sqlite3.Row, key: str, default: Any = None) -> Any:
        """Get optional column from row, returning default if column doesn't exist."""
        try:
            return row[key]
        except (KeyError, IndexError, sqlite3.OperationalError):
            return default

    def _row_to_event(self, row: sqlite3.Row) -> TelemetryEvent:
        return TelemetryEvent(
            id=row["id"],
            event_type=row["event_type"],
            event_category=row["event_category"],
            timestamp=row["timestamp"],
            received_at=row["received_at"],
            session_id=row["session_id"],
            correlation_id=row["correlation_id"],
            parent_event_id=row["parent_event_id"],
            attributes=types.MappingProxyType(self._deserialize_attributes(row["attributes"]) or {}),
            metrics=types.MappingProxyType(self._deserialize_metrics(row["metrics"]) or {})
            if row["metrics"]
            else None,
            expires_at=row["expires_at"],
        )

    def _row_to_session(self, row: sqlite3.Row) -> SessionSummary:
        return SessionSummary(
            session_id=row["session_id"],
            workspace_id=row["workspace_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            duration_ms=row["duration_ms"],
            status=row["status"],
            hooks_fired=row["hooks_fired"],
            hooks_succeeded=row["hooks_succeeded"],
            hooks_failed=row["hooks_failed"],
            agents_spawned=row["agents_spawned"],
            agents_completed=row["agents_completed"],
            agents_failed=row["agents_failed"],
            tmux_sessions_created=row["tmux_sessions_created"],
            tmux_sessions_killed=self._get_optional(row, "tmux_sessions_killed", 0),
            memory_saves=row["memory_saves"],
            memory_searches=row["memory_searches"],
            memory_deletes=self._get_optional(row, "memory_deletes", 0),
            workflow_started=row["workflow_started"],
            workflow_completed=row["workflow_completed"],
            workflow_aborted=self._get_optional(row, "workflow_aborted", 0),
            cli_commands=row["cli_commands"],
            cli_errors=row["cli_errors"],
            platform=row["platform"],
            python_version=row["python_version"],
            fork_agent_version=row["fork_agent_version"],
        )

    def _row_to_metric_bucket(self, row: sqlite3.Row) -> MetricBucket:
        return MetricBucket(
            id=row["id"],
            metric_name=row["metric_name"],
            metric_type=row["metric_type"],
            labels=types.MappingProxyType(
                self._deserialize_attributes(row["labels"]) if row["labels"] else {}
            ),
            labels_hash=row["labels_hash"],
            bucket_start=row["bucket_start"],
            bucket_duration=row["bucket_duration"],
            value_count=row["value_count"],
            value_sum=row["value_sum"],
            value_min=row["value_min"],
            value_max=row["value_max"],
            value_last=row["value_last"],
            updated_at=row["updated_at"],
        )

    def save(self, event: TelemetryEvent) -> None:
        self.save_batch([event])

    def save_batch(self, events: list[TelemetryEvent]) -> None:
        if not events:
            return

        with self._connection as conn:
            try:
                conn.executemany(
                    """INSERT OR REPLACE INTO telemetry_events
                       (id, event_type, event_category, timestamp, received_at, session_id,
                        correlation_id, parent_event_id, attributes, metrics, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            e.id,
                            e.event_type,
                            e.event_category,
                            e.timestamp,
                            e.received_at,
                            e.session_id,
                            e.correlation_id,
                            e.parent_event_id,
                            self._serialize_attributes(dict(e.attributes)),
                            self._serialize_metrics(dict(e.metrics) if e.metrics is not None else None),
                            e.expires_at,
                        )
                        for e in events
                    ],
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_by_id(self, event_id: str) -> TelemetryEvent | None:
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT * FROM telemetry_events WHERE id = ?",
                (event_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_event(row)

    def query(
        self,
        event_type: str | None = None,
        event_category: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TelemetryEvent]:
        where_clauses = []
        params: list[str | int] = []

        if event_type is not None:
            where_clauses.append("event_type = ?")
            params.append(event_type)
        if event_category is not None:
            where_clauses.append("event_category = ?")
            params.append(event_category)
        if session_id is not None:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        if correlation_id is not None:
            where_clauses.append("correlation_id = ?")
            params.append(correlation_id)
        if start_time is not None:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = (
            f"SELECT * FROM telemetry_events WHERE {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        with self._connection as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def count(
        self,
        event_type: str | None = None,
        event_category: str | None = None,
        session_id: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> int:
        where_clauses = []
        params: list[str | int] = []

        if event_type is not None:
            where_clauses.append("event_type = ?")
            params.append(event_type)
        if event_category is not None:
            where_clauses.append("event_category = ?")
            params.append(event_category)
        if session_id is not None:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        if start_time is not None:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT COUNT(*) as count FROM telemetry_events WHERE {where}"

        with self._connection as conn:
            cursor = conn.execute(query, params)
            return int(cursor.fetchone()["count"])

    def aggregate_metric(
        self,
        metric_name: str,
        labels: dict[str, str],
        _bucket_duration: int,
        start_time: int,
        end_time: int,
    ) -> list[MetricBucket]:
        labels_json = json.dumps(labels, sort_keys=True, separators=(",", ":"))
        labels_hash = hashlib.md5(labels_json.encode(), usedforsecurity=False).hexdigest()

        with self._connection as conn:
            cursor = conn.execute(
                """SELECT * FROM telemetry_metrics
                   WHERE metric_name = ? AND labels_hash = ? AND bucket_start >= ? AND bucket_start < ?
                   ORDER BY bucket_start DESC""",
                (metric_name, labels_hash, start_time, end_time),
            )
            return [self._row_to_metric_bucket(row) for row in cursor.fetchall()]

    def record_metric(
        self,
        metric_name: str,
        metric_type: str,
        value: float,
        labels: dict[str, str],
        bucket_duration: int = 60,
    ) -> None:
        now = int(datetime.now(UTC).timestamp())
        bucket_start = (now // bucket_duration) * bucket_duration

        labels_json = json.dumps(labels, sort_keys=True, separators=(",", ":"))
        labels_hash = hashlib.md5(labels_json.encode(), usedforsecurity=False).hexdigest()

        with self._connection as conn:
            # Try to update existing bucket
            cursor = conn.execute(
                """SELECT * FROM telemetry_metrics
                   WHERE metric_name = ? AND labels_hash = ? AND bucket_start = ? AND bucket_duration = ?""",
                (metric_name, labels_hash, bucket_start, bucket_duration),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing bucket
                conn.execute(
                    """UPDATE telemetry_metrics SET
                       value_count = value_count + 1,
                       value_sum = value_sum + ?,
                       value_min = COALESCE(MIN(value_min, ?), ?),
                       value_max = COALESCE(MAX(value_max, ?), ?),
                       value_last = ?,
                       updated_at = ?
                       WHERE id = ?""",
                    (value, value, value, value, value, value, now, existing["id"]),
                )
            else:
                # Insert new bucket
                conn.execute(
                    """INSERT INTO telemetry_metrics
                       (id, metric_name, metric_type, labels, labels_hash, bucket_start,
                        bucket_duration, value_count, value_sum, value_min, value_max, value_last, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        metric_name,
                        metric_type,
                        labels_json,
                        labels_hash,
                        bucket_start,
                        bucket_duration,
                        value,
                        value,
                        value,
                        value,
                        now,
                    ),
                )

    def get_session_summary(self, session_id: str) -> SessionSummary | None:
        with self._connection as conn:
            cursor = conn.execute(
                "SELECT * FROM telemetry_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_session(row)

    def save_session_summary(self, summary: SessionSummary) -> None:
        with self._connection as conn:
            conn.execute(
                """INSERT OR REPLACE INTO telemetry_sessions
                   (session_id, workspace_id, started_at, ended_at, duration_ms, status,
                    hooks_fired, hooks_succeeded, hooks_failed, agents_spawned, agents_completed,
                    agents_failed, tmux_sessions_created, tmux_sessions_killed, memory_saves, memory_searches,
                    memory_deletes, workflow_started, workflow_completed, workflow_aborted,
                    cli_commands, cli_errors, platform, python_version, fork_agent_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary.session_id,
                    summary.workspace_id,
                    summary.started_at,
                    summary.ended_at,
                    summary.duration_ms,
                    summary.status,
                    summary.hooks_fired,
                    summary.hooks_succeeded,
                    summary.hooks_failed,
                    summary.agents_spawned,
                    summary.agents_completed,
                    summary.agents_failed,
                    summary.tmux_sessions_created,
                    summary.tmux_sessions_killed,
                    summary.memory_saves,
                    summary.memory_searches,
                    summary.memory_deletes,
                    summary.workflow_started,
                    summary.workflow_completed,
                    summary.workflow_aborted,
                    summary.cli_commands,
                    summary.cli_errors,
                    summary.platform,
                    summary.python_version,
                    summary.fork_agent_version,
                ),
            )

    def list_sessions(
        self,
        status: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
    ) -> list[SessionSummary]:
        where_clauses = []
        params: list[str | int] = []

        if status is not None:
            where_clauses.append("status = ?")
            params.append(status)
        if start_time is not None:
            where_clauses.append("started_at >= ?")
            params.append(start_time)
        if end_time is not None:
            where_clauses.append("started_at <= ?")
            params.append(end_time)

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT * FROM telemetry_sessions WHERE {where} ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with self._connection as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_session(row) for row in cursor.fetchall()]

    def cleanup_expired(self) -> int:
        now = int(datetime.now(UTC).timestamp() * 1000)
        with self._connection as conn:
            cursor = conn.execute(
                "DELETE FROM telemetry_events WHERE expires_at < ?",
                (now,),
            )
            return cursor.rowcount

    def get_event_counts_by_type(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict[str, int]:
        where_clauses = []
        params: list[str | int] = []

        if start_time is not None:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT event_type, COUNT(*) as count FROM telemetry_events WHERE {where} GROUP BY event_type"

        with self._connection as conn:
            cursor = conn.execute(query, params)
            return {row["event_type"]: row["count"] for row in cursor.fetchall()}

    def get_event_counts_by_category(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict[str, int]:
        where_clauses = []
        params: list[str | int] = []

        if start_time is not None:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time is not None:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT event_category, COUNT(*) as count FROM telemetry_events WHERE {where} GROUP BY event_category"

        with self._connection as conn:
            cursor = conn.execute(query, params)
            return {row["event_category"]: row["count"] for row in cursor.fetchall()}
