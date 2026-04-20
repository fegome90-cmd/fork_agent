"""Telemetry service for tracking all system events."""

from __future__ import annotations

import logging
import os
import platform
import threading
from datetime import UTC, datetime
from typing import Any

from src.domain.entities.telemetry_event import (
    EventCategory,
    EventType,
    MetricBucket,
    SessionSummary,
    TelemetryEvent,
)
from src.domain.ports.telemetry_repository import TelemetryRepository

logger = logging.getLogger(__name__)


class TelemetryService:
    """Fachada para el sistema de telemetría.

    Provides a high-level API for tracking events and querying metrics.
    Uses buffering for efficient batch writes.
    """

    def __init__(
        self,
        repository: TelemetryRepository,
        buffer_size: int = 50,
        enabled: bool = True,
    ) -> None:
        self._repository = repository
        self._buffer: list[TelemetryEvent] = []
        self._buffer_size = buffer_size
        self._enabled = (
            enabled and os.environ.get("FORK_AGENT_TELEMETRY_ENABLED", "true").lower() != "false"
        )
        self._session_id: str | None = None
        self._session_start: int | None = None
        self._lock = threading.RLock()

        # Platform info
        self._platform = platform.system().lower()
        self._python_version = platform.python_version()
        self._fork_agent_version = self._get_version()

    def _get_version(self) -> str:
        """Get fork_agent version."""
        try:
            from importlib.metadata import version

            return version("fork_agent")
        except Exception:
            logger.debug("Failed to detect fork_agent version", exc_info=True)
            return "unknown"

    @property
    def session_id(self) -> str | None:
        """Current session ID."""
        return self._session_id

    @property
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self._enabled

    @property
    def repository(self) -> TelemetryRepository:
        """Access to the underlying repository for advanced queries."""
        return self._repository

    def start_session(self, session_id: str, workspace_id: str | None = None) -> None:
        """Start a new telemetry session."""
        if not self._enabled:
            return

        self._session_id = session_id
        self._session_start = int(datetime.now(UTC).timestamp() * 1000)

        # Create session summary
        summary = SessionSummary(
            session_id=session_id,
            workspace_id=workspace_id,
            started_at=self._session_start,
            status="active",
            platform=self._platform,
            python_version=self._python_version,
            fork_agent_version=self._fork_agent_version,
        )
        self._repository.save_session_summary(summary)

        # Track session start event
        self.track(
            EventType.SESSION_START,
            EventCategory.SESSION,
            {
                "workspace_id": workspace_id,
                "platform": self._platform,
                "python_version": self._python_version,
                "fork_agent_version": self._fork_agent_version,
            },
        )

    def end_session(self, reason: str = "normal") -> None:
        """End the current telemetry session."""
        if not self._enabled or not self._session_id:
            return

        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        duration_ms = now_ms - self._session_start if self._session_start else 0

        # Track session end event
        self.track(
            EventType.SESSION_END,
            EventCategory.SESSION,
            {
                "reason": reason,
                "duration_ms": duration_ms,
            },
            metrics={"duration_ms": float(duration_ms)},
        )

        # Flush buffer
        self.flush()

        # Update session summary
        session_id = self._session_id
        if session_id is None:
            return
        summary = self._repository.get_session_summary(session_id)
        if summary:
            from dataclasses import replace

            updated = replace(
                summary,
                ended_at=now_ms,
                duration_ms=duration_ms,
                status="ended" if reason == "normal" else "error",
            )
            self._repository.save_session_summary(updated)

        self._session_id = None
        self._session_start = None

    def track(
        self,
        event_type: str | EventType,
        event_category: str | EventCategory,
        attributes: dict[str, Any],
        metrics: dict[str, float] | None = None,
        correlation_id: str | None = None,
        parent_event_id: str | None = None,
        timestamp: int | None = None,
    ) -> str:
        """Track a telemetry event.

        Args:
            event_type: Type of event (e.g., "hook.fire")
            event_category: Category (e.g., "hook")
            attributes: Event-specific attributes
            metrics: Optional numeric metrics
            correlation_id: ID for linking related events
            parent_event_id: Parent event ID for hierarchies
            timestamp: Optional custom timestamp

        Returns:
            The event ID
        """
        if not self._enabled:
            return ""

        event = TelemetryEvent.create(
            event_type=event_type,
            event_category=event_category,
            attributes=attributes,
            session_id=self._session_id,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
            metrics=metrics,
            timestamp=timestamp,
        )

        # Add to buffer and update summary atomically
        with self._lock:
            self._buffer.append(event)

            # Flush if buffer is full
            if len(self._buffer) >= self._buffer_size:
                self.flush()

            # Update session summary while still holding lock to avoid race
            if self._session_id:
                self._update_session_summary(event)

        return event.id

    def _update_session_summary(self, event: TelemetryEvent) -> None:
        """Update session summary with event counts."""
        session_id = self._session_id
        if session_id is None:
            return
        summary = self._repository.get_session_summary(session_id)
        if not summary:
            return

        # Increment counters based on event type
        updates: dict[str, int] = {}

        if event.event_type == EventType.HOOK_FIRE:
            updates["hooks_fired"] = summary.hooks_fired + 1
        elif event.event_type == EventType.HOOK_SUCCESS:
            updates["hooks_succeeded"] = summary.hooks_succeeded + 1
        elif event.event_type == EventType.HOOK_FAIL:
            updates["hooks_failed"] = summary.hooks_failed + 1
        elif event.event_type == EventType.AGENT_SPAWN:
            updates["agents_spawned"] = summary.agents_spawned + 1
        elif event.event_type == EventType.AGENT_STOP:
            status = event.attributes.get("status", "completed")
            if status == "completed":
                updates["agents_completed"] = summary.agents_completed + 1
            else:
                updates["agents_failed"] = summary.agents_failed + 1
        elif event.event_type == EventType.TMUX_SESSION_CREATE:
            updates["tmux_sessions_created"] = summary.tmux_sessions_created + 1
        elif event.event_type == EventType.TMUX_SESSION_KILL:
            updates["tmux_sessions_killed"] = summary.tmux_sessions_killed + 1
        elif event.event_type == EventType.MEMORY_SAVE:
            updates["memory_saves"] = summary.memory_saves + 1
        elif event.event_type == EventType.MEMORY_SEARCH:
            updates["memory_searches"] = summary.memory_searches + 1
        elif event.event_type == EventType.MEMORY_DELETE:
            updates["memory_deletes"] = summary.memory_deletes + 1
        elif event.event_type in (EventType.WORKFLOW_OUTLINE, EventType.WORKFLOW_EXECUTE):
            updates["workflow_started"] = summary.workflow_started + 1
        elif event.event_type == EventType.WORKFLOW_SHIP:
            updates["workflow_completed"] = summary.workflow_completed + 1
        elif event.event_type == EventType.WORKFLOW_ABORT:
            updates["workflow_aborted"] = summary.workflow_aborted + 1
        elif event.event_type == EventType.CLI_COMMAND:
            updates["cli_commands"] = summary.cli_commands + 1
        elif event.event_type == EventType.CLI_ERROR:
            updates["cli_errors"] = summary.cli_errors + 1

        if updates:
            from dataclasses import replace

            updated = replace(summary, **updates)  # type: ignore[arg-type]
            self._repository.save_session_summary(updated)

    # Convenience methods for common events

    def track_hook_fire(
        self,
        hook_name: str,
        event_type: str,
        matcher: str,
        timeout_ms: int,
        critical: bool,
    ) -> str:
        """Track a hook being fired."""
        return self.track(
            EventType.HOOK_FIRE,
            EventCategory.HOOK,
            {
                "hook_name": hook_name,
                "event_type": event_type,
                "matcher": matcher,
                "timeout_ms": timeout_ms,
                "critical": critical,
            },
        )

    def track_hook_success(
        self,
        hook_name: str,
        event_type: str,
        duration_ms: int,
        output_preview: str = "",
    ) -> str:
        """Track a successful hook execution."""
        return self.track(
            EventType.HOOK_SUCCESS,
            EventCategory.HOOK,
            {
                "hook_name": hook_name,
                "event_type": event_type,
                "duration_ms": duration_ms,
                "output_preview": output_preview[:100],
            },
            metrics={"duration_ms": float(duration_ms)},
        )

    def track_hook_fail(
        self,
        hook_name: str,
        event_type: str,
        error_type: str,
        error_message: str,
        duration_ms: int,
        on_failure_policy: str,
    ) -> str:
        """Track a failed hook execution."""
        return self.track(
            EventType.HOOK_FAIL,
            EventCategory.HOOK,
            {
                "hook_name": hook_name,
                "event_type": event_type,
                "error_type": error_type,
                "error_message": error_message[:200],
                "duration_ms": duration_ms,
                "on_failure_policy": on_failure_policy,
            },
            metrics={"duration_ms": float(duration_ms)},
        )

    def track_agent_spawn(
        self,
        agent_id: str,
        agent_name: str,
        session_name: str,
        working_dir: str,
    ) -> str:
        """Track an agent being spawned."""
        return self.track(
            EventType.AGENT_SPAWN,
            EventCategory.AGENT,
            {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "session_name": session_name,
                "working_dir": working_dir,
            },
        )

    def track_agent_stop(
        self,
        agent_id: str,
        agent_name: str,
        duration_ms: int,
        status: str,
        exit_code: int = 0,
    ) -> str:
        """Track an agent stopping."""
        return self.track(
            EventType.AGENT_STOP,
            EventCategory.AGENT,
            {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "duration_ms": duration_ms,
                "status": status,
                "exit_code": exit_code,
            },
            metrics={"duration_ms": float(duration_ms)},
        )

    def track_tmux_session_create(
        self,
        session_name: str,
        session_type: str,
        created_by: str,
    ) -> str:
        """Track a tmux session being created."""
        return self.track(
            EventType.TMUX_SESSION_CREATE,
            EventCategory.TMUX,
            {
                "session_name": session_name,
                "session_type": session_type,
                "created_by": created_by,
            },
        )

    def track_tmux_session_kill(
        self,
        session_name: str,
        session_type: str,
        reason: str,
        duration_ms: int,
    ) -> str:
        """Track a tmux session being killed."""
        return self.track(
            EventType.TMUX_SESSION_KILL,
            EventCategory.TMUX,
            {
                "session_name": session_name,
                "session_type": session_type,
                "reason": reason,
                "duration_ms": duration_ms,
            },
            metrics={"duration_ms": float(duration_ms)},
        )

    def track_memory_save(
        self,
        observation_id: str,
        content_length: int,
        has_metadata: bool,
    ) -> str:
        """Track a memory save operation."""
        return self.track(
            EventType.MEMORY_SAVE,
            EventCategory.MEMORY,
            {
                "observation_id": observation_id,
                "content_length": content_length,
                "has_metadata": has_metadata,
            },
            metrics={"content_length": float(content_length)},
        )

    def track_memory_search(
        self,
        query_length: int,
        limit: int,
        results_count: int,
        duration_ms: int,
    ) -> str:
        """Track a memory search operation."""
        return self.track(
            EventType.MEMORY_SEARCH,
            EventCategory.MEMORY,
            {
                "query_length": query_length,
                "limit": limit,
                "results_count": results_count,
                "duration_ms": duration_ms,
            },
            metrics={
                "duration_ms": float(duration_ms),
                "results_count": float(results_count),
            },
        )

    def track_memory_delete(
        self,
        observation_id: str,
        session_id: str | None = None,
    ) -> str:
        """Track a memory delete operation."""
        return self.track(
            EventType.MEMORY_DELETE,
            EventCategory.MEMORY,
            {
                "observation_id": observation_id,
                "session_id": session_id,
            },
        )

    def track_workflow_outline(self, plan_id: str, task_count: int) -> str:
        """Track a workflow outline."""
        return self.track(
            EventType.WORKFLOW_OUTLINE,
            EventCategory.WORKFLOW,
            {
                "plan_id": plan_id,
                "task_count": task_count,
            },
            metrics={"task_count": float(task_count)},
        )

    def track_workflow_execute(self, plan_id: str, execute_id: str, task_count: int) -> str:
        """Track a workflow execute."""
        return self.track(
            EventType.WORKFLOW_EXECUTE,
            EventCategory.WORKFLOW,
            {
                "plan_id": plan_id,
                "execute_id": execute_id,
                "task_count": task_count,
            },
        )

    def track_workflow_verify(
        self,
        verify_id: str,
        tests_passed: int,
        tests_failed: int,
        unlock_ship: bool,
    ) -> str:
        """Track a workflow verify."""
        return self.track(
            EventType.WORKFLOW_VERIFY,
            EventCategory.WORKFLOW,
            {
                "verify_id": verify_id,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "unlock_ship": unlock_ship,
            },
            metrics={
                "tests_passed": float(tests_passed),
                "tests_failed": float(tests_failed),
            },
        )

    def track_workflow_ship(
        self, session_id: str, target_branch: str, duration_total_ms: int
    ) -> str:
        """Track a workflow ship."""
        return self.track(
            EventType.WORKFLOW_SHIP,
            EventCategory.WORKFLOW,
            {
                "session_id": session_id,
                "target_branch": target_branch,
                "duration_total_ms": duration_total_ms,
            },
            metrics={"duration_total_ms": float(duration_total_ms)},
        )

    def track_workflow_abort(
        self,
        session_id: str,
        phase: str,
        reason: str,
    ) -> str:
        """Track a workflow abort."""
        return self.track(
            EventType.WORKFLOW_ABORT,
            EventCategory.WORKFLOW,
            {
                "session_id": session_id,
                "phase": phase,
                "reason": reason,
            },
        )

    def track_cli_command(
        self,
        command_name: str,
        subcommand: str | None,
        args_count: int,
        duration_ms: int,
        exit_code: int,
    ) -> str:
        """Track a CLI command execution."""
        return self.track(
            EventType.CLI_COMMAND,
            EventCategory.CLI,
            {
                "command_name": command_name,
                "subcommand": subcommand,
                "args_count": args_count,
                "duration_ms": duration_ms,
                "exit_code": exit_code,
            },
            metrics={"duration_ms": float(duration_ms)},
        )

    def track_cli_error(
        self,
        command_name: str,
        error_type: str,
        error_message: str,
    ) -> str:
        """Track a CLI error."""
        return self.track(
            EventType.CLI_ERROR,
            EventCategory.CLI,
            {
                "command_name": command_name,
                "error_type": error_type,
                "error_message": error_message[:200],
            },
        )

    # Query methods

    def flush(self) -> None:
        """Flush the event buffer to storage."""
        with self._lock:
            if not self._buffer:
                return

            self._repository.save_batch(self._buffer)
            self._buffer.clear()

    def get_session_summary(self, session_id: str) -> SessionSummary | None:
        """Get summary for a session."""
        return self._repository.get_session_summary(session_id)

    def get_events(
        self,
        event_type: str | None = None,
        session_id: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
    ) -> list[TelemetryEvent]:
        """Query telemetry events."""
        return self._repository.query(
            event_type=event_type,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_metrics(
        self,
        metric_name: str,
        labels: dict[str, str],
        period: str = "24h",
    ) -> list[MetricBucket]:
        """Get aggregated metrics for a period.

        Args:
            metric_name: Name of the metric
            labels: Labels to filter by
            period: Time period (1h, 24h, 7d, 30d)
        """
        now = int(datetime.now(UTC).timestamp())

        period_seconds = {
            "1h": 3600,
            "24h": 86400,
            "7d": 7 * 86400,
            "30d": 30 * 86400,
        }

        duration = period_seconds.get(period, 86400)
        start_time = now - duration

        return self._repository.aggregate_metric(
            metric_name=metric_name,
            labels=labels,
            bucket_duration=3600,  # 1-hour buckets
            start_time=start_time,
            end_time=now,
        )

    def get_event_counts(self, period: str = "24h") -> dict[str, int]:
        """Get event counts by type for a period."""
        now = int(datetime.now(UTC).timestamp() * 1000)

        period_ms = {
            "1h": 3600000,
            "24h": 86400000,
            "7d": 7 * 86400000,
            "30d": 30 * 86400000,
        }

        duration = period_ms.get(period, 86400000)
        start_time = now - duration

        return self._repository.get_event_counts_by_type(start_time=start_time, end_time=now)

    def cleanup_expired(self) -> int:
        """Remove expired events."""
        return self._repository.cleanup_expired()

    # Export methods

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines: list[str] = []

        # Get current counts
        counts = self._repository.get_event_counts_by_category()

        # Session metrics
        if "session" in counts:
            lines.extend(
                [
                    "# HELP fork_agent_session_total Total sessions started",
                    "# TYPE fork_agent_session_total counter",
                    f"fork_agent_session_total {counts['session']}",
                ]
            )

        # Hook metrics
        if "hook" in counts:
            lines.extend(
                [
                    "# HELP fork_agent_hook_total Total hooks fired",
                    "# TYPE fork_agent_hook_total counter",
                    f"fork_agent_hook_total {counts['hook']}",
                ]
            )

        # Agent metrics
        if "agent" in counts:
            lines.extend(
                [
                    "# HELP fork_agent_agent_total Total agents spawned",
                    "# TYPE fork_agent_agent_total counter",
                    f"fork_agent_agent_total {counts['agent']}",
                ]
            )

        # Memory metrics
        if "memory" in counts:
            lines.extend(
                [
                    "# HELP fork_agent_memory_operations_total Total memory operations",
                    "# TYPE fork_agent_memory_operations_total counter",
                    f"fork_agent_memory_operations_total {counts['memory']}",
                ]
            )

        # Workflow metrics
        if "workflow" in counts:
            lines.extend(
                [
                    "# HELP fork_agent_workflow_total Total workflow events",
                    "# TYPE fork_agent_workflow_total counter",
                    f"fork_agent_workflow_total {counts['workflow']}",
                ]
            )

        # CLI metrics
        if "cli" in counts:
            lines.extend(
                [
                    "# HELP fork_agent_cli_commands_total Total CLI commands",
                    "# TYPE fork_agent_cli_commands_total counter",
                    f"fork_agent_cli_commands_total {counts['cli']}",
                ]
            )

        return "\n".join(lines)

    def export_json(self, period: str = "24h") -> dict[str, Any]:
        """Export metrics as JSON."""
        return {
            "period": period,
            "event_counts_by_type": self.get_event_counts(period),
            "event_counts_by_category": self._repository.get_event_counts_by_category(),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "hooks_fired": s.hooks_fired,
                    "agents_spawned": s.agents_spawned,
                    "memory_saves": s.memory_saves,
                    "workflow_started": s.workflow_started,
                    "cli_commands": s.cli_commands,
                }
                for s in self._repository.list_sessions(limit=10)
            ],
        }
