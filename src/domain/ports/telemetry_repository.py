"""Repository port for telemetry events."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.telemetry_event import MetricBucket, SessionSummary, TelemetryEvent


class TelemetryRepository(Protocol):
    """Protocol for telemetry event persistence.

    Follows the Repository pattern from DDD.
    Implementations should handle:
    - Event storage with buffering/batching
    - Metric aggregation
    - TTL-based cleanup
    """

    def save(self, event: TelemetryEvent) -> None:
        """Save a single telemetry event.

        Args:
            event: The telemetry event to save
        """
        ...

    def save_batch(self, events: list[TelemetryEvent]) -> None:
        """Save multiple telemetry events in a batch.

        More efficient than individual saves for high-volume scenarios.

        Args:
            events: List of telemetry events to save
        """
        ...

    def get_by_id(self, event_id: str) -> TelemetryEvent | None:
        """Get a telemetry event by ID.

        Args:
            event_id: The event's unique identifier

        Returns:
            The event if found, None otherwise
        """
        ...

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
        """Query telemetry events with filters.

        Args:
            event_type: Filter by event type (e.g., "hook.fire")
            event_category: Filter by category (e.g., "hook")
            session_id: Filter by session ID
            correlation_id: Filter by correlation ID
            start_time: Unix timestamp (ms) for start of range
            end_time: Unix timestamp (ms) for end of range
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching events
        """
        ...

    def count(
        self,
        event_type: str | None = None,
        event_category: str | None = None,
        session_id: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> int:
        """Count telemetry events matching filters.

        Args:
            event_type: Filter by event type
            event_category: Filter by category
            session_id: Filter by session ID
            start_time: Unix timestamp (ms) for start of range
            end_time: Unix timestamp (ms) for end of range

        Returns:
            Number of matching events
        """
        ...

    def aggregate_metric(
        self,
        metric_name: str,
        labels: dict[str, str],
        bucket_duration: int,
        start_time: int,
        end_time: int,
    ) -> list[MetricBucket]:
        """Query pre-aggregated metrics.

        Args:
            metric_name: Name of the metric
            labels: Labels to filter by
            bucket_duration: Bucket duration in seconds (60, 3600, 86400)
            start_time: Unix timestamp (seconds) for start of range
            end_time: Unix timestamp (seconds) for end of range

        Returns:
            List of metric buckets
        """
        ...

    def record_metric(
        self,
        metric_name: str,
        metric_type: str,
        value: float,
        labels: dict[str, str],
        bucket_duration: int = 60,
    ) -> None:
        """Record a metric value for aggregation.

        Args:
            metric_name: Name of the metric
            metric_type: Type (counter, gauge, histogram)
            value: The value to record
            labels: Labels for the metric
            bucket_duration: Bucket duration in seconds
        """
        ...

    def get_session_summary(self, session_id: str) -> SessionSummary | None:
        """Get aggregated summary for a session.

        Args:
            session_id: The session ID

        Returns:
            Session summary if found, None otherwise
        """
        ...

    def save_session_summary(self, summary: SessionSummary) -> None:
        """Save or update a session summary.

        Args:
            summary: The session summary to save
        """
        ...

    def list_sessions(
        self,
        status: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
    ) -> list[SessionSummary]:
        """List sessions with filters.

        Args:
            status: Filter by status (active, ended, error)
            start_time: Unix timestamp (ms) for start of range
            end_time: Unix timestamp (ms) for end of range
            limit: Maximum number of results

        Returns:
            List of session summaries
        """
        ...

    def cleanup_expired(self) -> int:
        """Remove expired events based on TTL.

        Returns:
            Number of events removed
        """
        ...

    def get_event_counts_by_type(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict[str, int]:
        """Get event counts grouped by type.

        Args:
            start_time: Unix timestamp (ms) for start of range
            end_time: Unix timestamp (ms) for end of range

        Returns:
            Dict mapping event_type to count
        """
        ...

    def get_event_counts_by_category(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict[str, int]:
        """Get event counts grouped by category.

        Args:
            start_time: Unix timestamp (ms) for start of range
            end_time: Unix timestamp (ms) for end of range

        Returns:
            Dict mapping event_category to count
        """
        ...
