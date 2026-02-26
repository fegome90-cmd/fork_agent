"""Telemetry event entity for tracking all system events."""

from __future__ import annotations

import json
import types
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EventCategory(StrEnum):
    """Categories of telemetry events."""

    SESSION = "session"
    HOOK = "hook"
    AGENT = "agent"
    TMUX = "tmux"
    MEMORY = "memory"
    WORKFLOW = "workflow"
    CLI = "cli"
    TRACE = "trace"
    ERROR = "error"


class EventType(StrEnum):
    """Standard event types for telemetry."""

    # Session events
    SESSION_START = "session.start"
    SESSION_END = "session.end"

    # Hook events
    HOOK_FIRE = "hook.fire"
    HOOK_SUCCESS = "hook.success"
    HOOK_FAIL = "hook.fail"

    # Agent events
    AGENT_SPAWN = "agent.spawn"
    AGENT_STOP = "agent.stop"
    AGENT_HEALTH_CHECK = "agent.health_check"

    # Tmux events
    TMUX_SESSION_CREATE = "tmux.session.create"
    TMUX_SESSION_KILL = "tmux.session.kill"
    TMUX_SESSION_LIST = "tmux.session.list"

    # Memory events
    MEMORY_SAVE = "memory.save"
    MEMORY_SEARCH = "memory.search"
    MEMORY_LIST = "memory.list"
    MEMORY_DELETE = "memory.delete"

    # Workflow events
    WORKFLOW_OUTLINE = "workflow.outline"
    WORKFLOW_EXECUTE = "workflow.execute"
    WORKFLOW_VERIFY = "workflow.verify"
    WORKFLOW_SHIP = "workflow.ship"
    WORKFLOW_ABORT = "workflow.abort"

    # CLI events
    CLI_COMMAND = "cli.command"
    CLI_ERROR = "cli.error"

    # Trace events
    TRACE_SPAN_START = "trace.span.start"
    TRACE_SPAN_END = "trace.span.end"


# Default retention periods (in days)
RETENTION_DAYS: dict[EventCategory, int] = {
    EventCategory.SESSION: 90,
    EventCategory.HOOK: 30,
    EventCategory.AGENT: 30,
    EventCategory.TMUX: 30,
    EventCategory.MEMORY: 30,
    EventCategory.WORKFLOW: 90,
    EventCategory.CLI: 30,
    EventCategory.TRACE: 7,
    EventCategory.ERROR: 90,
}


@dataclass(frozen=True)
class TelemetryEvent:
    """Immutable telemetry event entity.

    Represents a single telemetry event in the system.
    All events are append-only and immutable.
    """

    id: str
    event_type: str
    event_category: str
    timestamp: int  # Unix timestamp in milliseconds
    received_at: int  # Unix timestamp in milliseconds
    attributes: Mapping[str, Any]
    session_id: str | None = None
    correlation_id: str | None = None
    parent_event_id: str | None = None
    metrics: Mapping[str, float] | None = None
    expires_at: int | None = None  # Unix timestamp for TTL

    @classmethod
    def create(
        cls,
        event_type: str | EventType,
        event_category: str | EventCategory,
        attributes: dict[str, Any],
        session_id: str | None = None,
        correlation_id: str | None = None,
        parent_event_id: str | None = None,
        metrics: dict[str, float] | None = None,
        timestamp: int | None = None,
    ) -> TelemetryEvent:
        """Factory method to create a new telemetry event.

        Automatically generates ID, timestamps, and expiration.
        """
        now_ts = datetime.now(UTC).timestamp()
        now_ms = int(now_ts * 1000)

        # Calculate expiration based on category
        category = (
            EventCategory(event_category) if isinstance(event_category, str) else event_category
        )
        retention_days = RETENTION_DAYS.get(category, 30)
        expires_at = int((now_ts + retention_days * 86400) * 1000)

        return cls(
            id=str(uuid.uuid4()),
            event_type=event_type.value if isinstance(event_type, EventType) else event_type,
            event_category=category.value,
            timestamp=timestamp or now_ms,
            received_at=now_ms,
            attributes=types.MappingProxyType(attributes),
            session_id=session_id,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
            metrics=types.MappingProxyType(metrics) if metrics is not None else None,
            expires_at=expires_at,
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "timestamp": self.timestamp,
            "received_at": self.received_at,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "attributes": json.dumps(dict(self.attributes)),
            "metrics": json.dumps(dict(self.metrics)) if self.metrics else None,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TelemetryEvent:
        """Deserialize from JSON dict."""
        attrs_raw = (
            json.loads(data["attributes"])
            if isinstance(data["attributes"], str)
            else data["attributes"]
        )
        metrics_raw = (
            json.loads(data["metrics"])
            if data.get("metrics") and isinstance(data["metrics"], str)
            else data.get("metrics")
        )
        return cls(
            id=data["id"],
            event_type=data["event_type"],
            event_category=data["event_category"],
            timestamp=data["timestamp"],
            received_at=data["received_at"],
            session_id=data.get("session_id"),
            correlation_id=data.get("correlation_id"),
            parent_event_id=data.get("parent_event_id"),
            attributes=types.MappingProxyType(attrs_raw),
            metrics=types.MappingProxyType(metrics_raw) if metrics_raw is not None else None,
            expires_at=data.get("expires_at"),
        )


@dataclass(frozen=True)
class MetricBucket:
    """Pre-aggregated metric bucket for time-series queries."""

    id: str
    metric_name: str
    metric_type: str  # counter, gauge, histogram
    labels: Mapping[str, str]
    labels_hash: str
    bucket_start: int  # Unix timestamp in seconds
    bucket_duration: int  # Duration in seconds
    value_count: int
    value_sum: float
    value_min: float | None
    value_max: float | None
    value_last: float | None
    updated_at: int


@dataclass(frozen=True)
class SessionSummary:
    """Summary of a telemetry session."""

    session_id: str
    workspace_id: str | None = None
    started_at: int | None = None
    ended_at: int | None = None
    duration_ms: int | None = None
    status: str = "active"

    # Aggregated metrics
    hooks_fired: int = 0
    hooks_succeeded: int = 0
    hooks_failed: int = 0
    agents_spawned: int = 0
    agents_completed: int = 0
    agents_failed: int = 0
    tmux_sessions_created: int = 0
    memory_saves: int = 0
    memory_searches: int = 0
    workflow_started: int = 0
    workflow_completed: int = 0
    cli_commands: int = 0
    cli_errors: int = 0

    # Environment
    platform: str | None = None
    python_version: str | None = None
    fork_agent_version: str | None = None
