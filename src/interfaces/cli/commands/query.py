"""Query command for structured event queries - FASE 4 UX MVP.

Uses structured queries (not FTS) with LIMIT K + Python filtering.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from src.interfaces.cli.dependencies import get_memory_service

app = typer.Typer(help="Query memory events with structured filters.")


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current: Any = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            return Path(current.params["db_path"])
        current = current.parent if hasattr(current, "parent") else None
    return None


def _format_timestamp(ts_ms: int) -> str:
    """Format milliseconds timestamp to human-readable string."""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_timestamp_short(ts_ms: int) -> str:
    """Format milliseconds timestamp to short time string."""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
    return dt.strftime("%H:%M:%S")


def _truncate(text: str, max_len: int = 80) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _build_summary(obs) -> str:
    """Build summary from observation content and metadata."""
    content = obs.content or ""

    # For agent_message, show message_type
    extra = obs.metadata.get("extra", {}) if obs.metadata else {}
    event_type = obs.metadata.get("event_type", "") if obs.metadata else ""

    if event_type == "agent_message":
        msg_type = extra.get("message_type", "")
        if msg_type:
            return f"{msg_type}: {_truncate(content, 60)}"

    return _truncate(content)


def _build_indicators(obs) -> str:
    """Build indicator flags from metadata."""
    indicators = []

    extra = obs.metadata.get("extra", {}) if obs.metadata else {}

    if extra.get("payload_truncated"):
        indicators.append("TRUNC")

    if extra.get("important"):
        indicators.append("IMP")

    return " ".join(indicators)


@app.command()
def query(
    ctx: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "-a", help="Filter by agent ID")] = "",
    run: Annotated[str | None, typer.Option("--run", "-r", help="Filter by run ID")] = None,
    event_type: Annotated[
        str | None, typer.Option("--event-type", "-e", help="Filter by event type")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
    scan_limit: Annotated[
        int,
        typer.Option("--scan-limit", help="Max observations to scan (safety limit)"),
    ] = 1000,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Time filter (e.g., '24h', '7d', or ISO date)"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """Query memory events with structured filters.

    Examples:
        memory query --agent agent1:0 --limit 10
        memory query --run run-abc123 --event-type task_completed
        memory query --since 24h --json
    """
    db_path = _get_db_path_from_context(ctx)
    memory = get_memory_service(db_path)

    # Fetch observations with scan_limit (safety)
    observations = memory.get_recent(limit=scan_limit, offset=0)

    # Filter by agent_id or from_agent_id
    if agent:
        filtered = []
        for obs in observations:
            if not obs.metadata:
                continue
            agent_id = obs.metadata.get("agent_id", "")
            from_agent = obs.metadata.get("extra", {}).get("from_agent_id", "")
            if agent in agent_id or agent in from_agent:
                filtered.append(obs)
        observations = filtered

    # Filter by run_id
    if run:
        observations = [
            obs for obs in observations if obs.metadata and obs.metadata.get("run_id") == run
        ]

    # Filter by event_type
    if event_type:
        observations = [
            obs
            for obs in observations
            if obs.metadata and obs.metadata.get("event_type") == event_type
        ]

    # Filter by time (since)
    if since:
        # Parse since parameter
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        cutoff_ms = None

        if since.endswith("h"):
            hours = int(since[:-1])
            cutoff_ms = now_ms - (hours * 3600 * 1000)
        elif since.endswith("d"):
            days = int(since[:-1])
            cutoff_ms = now_ms - (days * 86400 * 1000)
        else:
            # Try ISO date
            try:
                dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                cutoff_ms = int(dt.timestamp() * 1000)
            except ValueError:
                typer.echo(f"Invalid --since format: {since}", err=True)
                raise typer.Exit(1)  # noqa: B904
        if cutoff_ms:
            observations = [obs for obs in observations if obs.timestamp >= cutoff_ms]

    # Sort by timestamp DESC
    observations.sort(key=lambda o: o.timestamp, reverse=True)

    # Apply limit
    observations = observations[:limit]

    if not observations:
        typer.echo("No events found matching criteria.")
        return

    # Output
    if json_output:
        output = [
            {
                "id": obs.id,
                "timestamp": obs.timestamp,
                "timestamp_iso": _format_timestamp(obs.timestamp),
                "event_type": obs.metadata.get("event_type") if obs.metadata else None,
                "run_id": obs.metadata.get("run_id") if obs.metadata else None,
                "task_id": obs.metadata.get("task_id") if obs.metadata else None,
                "agent_id": obs.metadata.get("agent_id") if obs.metadata else None,
                "summary": _build_summary(obs),
                "indicators": _build_indicators(obs),
            }
            for obs in observations
        ]
        typer.echo(json.dumps(output, indent=2))
    else:
        # Table output
        typer.echo(f"Found {len(observations)} events:\n")

        for obs in observations:
            ts = _format_timestamp(obs.timestamp)
            event = obs.metadata.get("event_type", "unknown") if obs.metadata else "unknown"
            summary = _build_summary(obs)
            run_id = obs.metadata.get("run_id", "-") if obs.metadata else "-"
            task_id = obs.metadata.get("task_id", "-") if obs.metadata else "-"
            indicators = _build_indicators(obs)

            indicator_str = f" [{indicators}]" if indicators else ""

            typer.echo(f"{ts} | {event:20} | {summary:40} | {run_id}/{task_id}{indicator_str}")


@app.command()
def timeline(
    ctx: typer.Context,
    run: Annotated[str, typer.Argument(help="Run ID to show timeline for")],
    scan_limit: Annotated[
        int,
        typer.Option("--scan-limit", help="Max observations to scan"),
    ] = 1000,
) -> None:
    """Show event timeline for a specific run.

    Events are ordered chronologically (ASC).

    Example:
        memory timeline run-abc123
    """
    db_path = _get_db_path_from_context(ctx)
    memory = get_memory_service(db_path)

    # Fetch observations with scan_limit
    observations = memory.get_recent(limit=scan_limit, offset=0)

    # Filter by run_id
    filtered = [obs for obs in observations if obs.metadata and obs.metadata.get("run_id") == run]

    if not filtered:
        typer.echo(f"No events found for run: {run}")
        return

    # Sort by timestamp ASC (chronological)
    filtered.sort(key=lambda o: o.timestamp)

    typer.echo(f"Timeline for run: {run} ({len(filtered)} events)\n")

    for obs in filtered:
        ts = _format_timestamp_short(obs.timestamp)
        meta = obs.metadata or {}
        event_type = meta.get("event_type", "unknown")

        # Add message_type for agent_message
        extra = meta.get("extra", {})
        if event_type == "agent_message" and extra.get("message_type"):
            event_type = f"{event_type}:{extra['message_type']}"

        # Build agent/session info
        agent_id = meta.get("agent_id", "-")
        session_name = meta.get("session_name", "")
        task_id = meta.get("task_id", "-")

        agent_str = f"{agent_id}"
        if session_name and session_name != agent_id.split(":")[0]:
            agent_str = f"{session_name}"

        # Build status
        status = ""
        if meta.get("success") is True:
            status = "✓"
        elif meta.get("success") is False:
            error = meta.get("error_message", "")
            status = f"✗ ({error[:30]}...)" if len(error) > 30 else f"✗ ({error})"

        typer.echo(f"{ts} | {event_type:25} | {agent_str:20} | {task_id:15} | {status}")
