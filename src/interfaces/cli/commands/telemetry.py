"""Telemetry CLI commands for fork_agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer(help="Telemetry commands for fork_agent.")


def _format_timestamp(ts_ms: int | None) -> str:
    """Format milliseconds timestamp to human-readable string."""
    if ts_ms is None:
        return "N/A"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(ms: int) -> str:
    """Format milliseconds to human-readable duration."""
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context.

    For subcommands (telemetry status), we need to traverse up to find
    the root context that has the db_path parameter.
    """
    # Walk up the context tree to find db_path
    current = ctx
    while current:
        if hasattr(current, 'params') and 'db_path' in current.params:
            return Path(current.params['db_path'])
        current = current.parent if hasattr(current, 'parent') else None

    return None


@app.command()
def status(
    ctx: typer.Context,
) -> None:
    """Show telemetry status and summary."""
    db_path = _get_db_path_from_context(ctx)
    telemetry = get_telemetry_service(db_path)

    typer.echo("=" * 60)
    typer.echo("  FORK_AGENT TELEMETRY STATUS")
    typer.echo("=" * 60)
    typer.echo(f"\nEnabled: {telemetry.is_enabled}")
    typer.echo(f"Session ID: {telemetry.session_id or 'No active session'}")
    typer.echo("\n--- Event Counts (Last 24h) ---")

    counts = telemetry.get_event_counts("24h")
    if counts:
        for event_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            typer.echo(f"  {event_type}: {count}")
    else:
        typer.echo("  No events recorded")

    typer.echo("\n--- Event Counts by Category (Last 24h) ---")
    # Group by category
    by_category: dict[str, int] = {}
    for event_type, count in counts.items():
        category = event_type.split(".")[0]
        by_category[category] = by_category.get(category, 0) + count

    if by_category:
        for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
            typer.echo(f"  {category}: {count}")
    else:
        typer.echo("  No events recorded")

    typer.echo("\n--- Recent Sessions ---")
    sessions = telemetry.repository.list_sessions(limit=5)  # type: ignore[attr-defined]
    if sessions:
        for s in sessions:
            typer.echo(
                f"  {s.session_id[:12]}... | {_format_timestamp(s.started_at)} | {s.status} | {_format_duration(s.duration_ms or 0)}"
            )
    else:
        typer.echo("  No sessions recorded")

    typer.echo()


@app.command()
def metrics(
    _ctx: typer.Context,
    name: Annotated[
        str, typer.Option("--name", "-n", help="Metric name to query")
    ] = "hook.fire.count",
    period: Annotated[
        str, typer.Option("--period", "-p", help="Time period (1h, 24h, 7d, 30d)")
    ] = "24h",
    labels_json: Annotated[
        str | None,
        typer.Option("--labels", "-l", help='JSON labels, e.g. {"hook_name": "test"}'),
    ] = None,
) -> None:
    """Show aggregated metrics."""
    import json

    telemetry = get_telemetry_service()

    labels = {}
    if labels_json:
        try:
            labels = json.loads(labels_json)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: Invalid JSON for labels: {e}", err=True)
            raise typer.Exit(1) from e

    typer.echo(f"Metrics: {name}")
    typer.echo(f"Period: {period}")
    typer.echo(f"Labels: {labels or 'all'}")
    typer.echo("-" * 40)

    buckets = telemetry.get_metrics(name, labels, period)

    if buckets:
        typer.echo(f"Found {len(buckets)} buckets:\n")
        for bucket in buckets:
            typer.echo(f"  Bucket: {_format_timestamp(bucket.bucket_start * 1000)}")
            typer.echo(f"    Count: {bucket.value_count}")
            typer.echo(f"    Sum: {bucket.value_sum:.2f}")
            if bucket.value_min is not None:
                typer.echo(f"    Min: {bucket.value_min:.2f}")
            if bucket.value_max is not None:
                typer.echo(f"    Max: {bucket.value_max:.2f}")
            if bucket.value_last is not None:
                typer.echo(f"    Last: {bucket.value_last:.2f}")
            typer.echo()
    else:
        typer.echo("No metrics found for the given criteria.")


@app.command()
def events(
    _ctx: typer.Context,
    event_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Event type filter")
    ] = None,
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Category filter")
    ] = None,
    session: Annotated[
        str | None, typer.Option("--session", "-s", help="Session ID filter")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max events to show")] = 20,
) -> None:
    """Show recent telemetry events."""
    telemetry = get_telemetry_service()

    # Get all matching events (no limit initially)
    events = telemetry.get_events(
        event_type=event_type,
        session_id=session,
        limit=1000,  # Get all, filter, then slice
    )

    # Filter by category first
    if category:
        events = [e for e in events if e.event_category == category]

    # Then apply limit
    if limit:
        events = events[:limit]

    typer.echo(f"Showing {len(events)} events:\n")

    for e in events:
        typer.echo(f"[{e.event_type}] {_format_timestamp(e.timestamp)}")
        typer.echo(f"  Session: {e.session_id or 'N/A'}")
        # Show first few attributes
        attrs = dict(e.attributes)
        if attrs:
            preview = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:3])
            typer.echo(f"  Attrs: {preview}")
        typer.echo()


@app.command()
def session(
    _ctx: typer.Context,
    session_id: Annotated[str, typer.Argument(help="Session ID to show")],
) -> None:
    """Show detailed session summary."""
    telemetry = get_telemetry_service()

    summary = telemetry.get_session_summary(session_id)

    if not summary:
        typer.echo(f"Session '{session_id}' not found.", err=True)
        raise typer.Exit(1)

    typer.echo("=" * 60)
    typer.echo(f"  SESSION: {summary.session_id}")
    typer.echo("=" * 60)

    typer.echo(f"\nStatus: {summary.status}")
    typer.echo(f"Started: {_format_timestamp(summary.started_at)}")
    typer.echo(f"Ended: {_format_timestamp(summary.ended_at)}")
    typer.echo(f"Duration: {_format_duration(summary.duration_ms or 0)}")
    typer.echo(f"Workspace: {summary.workspace_id or 'N/A'}")

    typer.echo("\n--- Hooks ---")
    typer.echo(f"  Fired: {summary.hooks_fired}")
    typer.echo(f"  Succeeded: {summary.hooks_succeeded}")
    typer.echo(f"  Failed: {summary.hooks_failed}")

    typer.echo("\n--- Agents ---")
    typer.echo(f"  Spawned: {summary.agents_spawned}")
    typer.echo(f"  Completed: {summary.agents_completed}")
    typer.echo(f"  Failed: {summary.agents_failed}")

    typer.echo("\n--- Tmux ---")
    typer.echo(f"  Sessions Created: {summary.tmux_sessions_created}")
    typer.echo(f"  Sessions Killed: {summary.tmux_sessions_killed}")

    typer.echo("\n--- Memory ---")
    typer.echo(f"  Saves: {summary.memory_saves}")
    typer.echo(f"  Searches: {summary.memory_searches}")
    typer.echo(f"  Deletes: {summary.memory_deletes}")

    typer.echo("\n--- Workflow ---")
    typer.echo(f"  Started: {summary.workflow_started}")
    typer.echo(f"  Completed: {summary.workflow_completed}")
    typer.echo(f"  Aborted: {summary.workflow_aborted}")

    typer.echo("\n--- CLI ---")
    typer.echo(f"  Commands: {summary.cli_commands}")
    typer.echo(f"  Errors: {summary.cli_errors}")

    typer.echo("\n--- Environment ---")
    typer.echo(f"  Platform: {summary.platform or 'N/A'}")
    typer.echo(f"  Python: {summary.python_version or 'N/A'}")
    typer.echo(f"  fork_agent: {summary.fork_agent_version or 'N/A'}")

    typer.echo()


@app.command()
def export(
    _ctx: typer.Context,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Export format: prometheus, json")
    ] = "prometheus",
    period: Annotated[
        str, typer.Option("--period", "-p", help="Time period (1h, 24h, 7d, 30d)")
    ] = "24h",
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Output file (stdout if not specified)")
    ] = None,
) -> None:
    """Export telemetry data in various formats."""
    telemetry = get_telemetry_service()

    if format == "prometheus":
        content = telemetry.export_prometheus()
    elif format == "json":
        content = json.dumps(telemetry.export_json(period), indent=2)
    else:
        typer.echo(f"Error: Unknown format '{format}'. Use 'prometheus' or 'json'.", err=True)
        raise typer.Exit(1)

    if output:
        from pathlib import Path

        Path(output).write_text(content)
        typer.echo(f"Exported to {output}")
    else:
        typer.echo(content)


@app.command()
def cleanup(
    _ctx: typer.Context,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be deleted without deleting")
    ] = False,
    confirm: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Clean up expired telemetry events."""
    telemetry = get_telemetry_service()

    if dry_run:
        # Estimate expired count
        # For dry run, we'll just show the current counts
        counts = telemetry.get_event_counts("30d")
        total = sum(counts.values())
        typer.echo("[DRY RUN] Would clean up expired events.")
        typer.echo(f"[DRY RUN] Total events in last 30 days: {total}")
        typer.echo("[DRY RUN] Run without --dry-run to actually delete.")
        return

    if not confirm:
        typer.echo("This will permanently delete all expired telemetry events.")
        typer.echo(
            "Expired events are those past their retention period (based on event category)."
        )
        if not typer.confirm("Continue?"):
            typer.echo("Aborted.")
            return

    deleted = telemetry.cleanup_expired()
    typer.echo(f"Deleted {deleted} expired events.")


@app.command()
def dashboard(
    _ctx: typer.Context,
    period: Annotated[
        str, typer.Option("--period", "-p", help="Time period (1h, 24h, 7d, 30d)")
    ] = "24h",
) -> None:
    """Show telemetry dashboard with key metrics."""
    telemetry = get_telemetry_service()

    counts = telemetry.get_event_counts(period)
    by_category: dict[str, int] = {}
    for event_type, count in counts.items():
        category = event_type.split(".")[0]
        by_category[category] = by_category.get(category, 0) + count

    # Get session stats
    sessions = telemetry.repository.list_sessions(status="ended", limit=100)  # type: ignore[attr-defined]

    # Calculate averages
    ended_sessions = [s for s in sessions if s.duration_ms]
    avg_duration = (
        sum(s.duration_ms for s in ended_sessions if s.duration_ms) / len(ended_sessions)
        if ended_sessions
        else 0
    )

    active_sessions = telemetry.repository.list_sessions(status="active", limit=100)  # type: ignore[attr-defined]

    # Build dashboard
    typer.echo()
    typer.echo("╔" + "═" * 58 + "╗")
    typer.echo("║" + " " * 15 + "FORK_AGENT TELEMETRY" + " " * 20 + "║")
    typer.echo("║" + f" Period: Last {period}".ljust(58) + "║")
    typer.echo("╠" + "═" * 58 + "╣")

    # Sessions
    typer.echo("║ SESSIONS".ljust(59) + "║")
    typer.echo("║" + f"  Total: {by_category.get('session', 0)} events".ljust(58) + "║")
    typer.echo("║" + f"  Active: {len(active_sessions)}".ljust(58) + "║")
    typer.echo("║" + f"  Avg duration: {_format_duration(int(avg_duration))}".ljust(58) + "║")

    # Hooks
    hook_fires = counts.get("hook.fire", 0)
    hook_success = counts.get("hook.success", 0)
    success_rate = (hook_success / hook_fires * 100) if hook_fires > 0 else 0

    typer.echo("║ HOOKS".ljust(59) + "║")
    typer.echo("║" + f"  Fired: {hook_fires}".ljust(58) + "║")
    typer.echo("║" + f"  Success rate: {success_rate:.1f}%".ljust(58) + "║")

    # Agents
    agent_spawns = counts.get("agent.spawn", 0)
    agent_stops = counts.get("agent.stop", 0)

    typer.echo("║ AGENTS".ljust(59) + "║")
    typer.echo("║" + f"  Spawned: {agent_spawns}".ljust(58) + "║")
    typer.echo("║" + f"  Stopped: {agent_stops}".ljust(58) + "║")

    # Tmux
    tmux_creates = counts.get("tmux.session.create", 0)
    tmux_kills = counts.get("tmux.session.kill", 0)

    typer.echo("║ TMUX".ljust(59) + "║")
    typer.echo("║" + f"  Sessions created: {tmux_creates}".ljust(58) + "║")
    typer.echo("║" + f"  Sessions killed: {tmux_kills}".ljust(58) + "║")

    # Memory
    mem_saves = counts.get("memory.save", 0)
    mem_searches = counts.get("memory.search", 0)
    mem_deletes = counts.get("memory.delete", 0)

    typer.echo("║ MEMORY".ljust(59) + "║")
    typer.echo("║" + f"  Saves: {mem_saves}".ljust(58) + "║")
    typer.echo("║" + f"  Searches: {mem_searches}".ljust(58) + "║")
    typer.echo("║" + f"  Deletes: {mem_deletes}".ljust(58) + "║")

    # Workflow
    wf_outline = counts.get("workflow.outline", 0)
    wf_ship = counts.get("workflow.ship", 0)
    wf_abort = counts.get("workflow.abort", 0)
    wf_completion = (wf_ship / wf_outline * 100) if wf_outline > 0 else 0

    typer.echo("║ WORKFLOW".ljust(59) + "║")
    typer.echo("║" + f"  Outlines: {wf_outline}".ljust(58) + "║")
    typer.echo("║" + f"  Completed: {wf_ship}".ljust(58) + "║")
    typer.echo("║" + f"  Aborted: {wf_abort}".ljust(58) + "║")
    typer.echo("║" + f"  Completion rate: {wf_completion:.1f}%".ljust(58) + "║")

    # CLI
    cli_cmds = counts.get("cli.command", 0)
    cli_errors = counts.get("cli.error", 0)
    cli_error_rate = (cli_errors / cli_cmds * 100) if cli_cmds > 0 else 0

    typer.echo("║ CLI".ljust(59) + "║")
    typer.echo("║" + f"  Commands: {cli_cmds}".ljust(58) + "║")
    typer.echo("║" + f"  Errors: {cli_errors} ({cli_error_rate:.1f}%)".ljust(58) + "║")

    typer.echo("╚" + "═" * 58 + "╝")
