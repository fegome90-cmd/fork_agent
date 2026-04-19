"""Stats command for CLI - shows database statistics."""

from __future__ import annotations

from pathlib import Path

import typer

from src.infrastructure.persistence.container import get_default_db_path
from src.infrastructure.persistence.health_check import HealthCheckService
from src.infrastructure.persistence.query_logger import get_query_logger
from src.interfaces.cli.dependencies import get_health_check_service, get_telemetry_service

app = typer.Typer()

DEFAULT_DB_PATH = get_default_db_path()


def _get_health_service_from_context(ctx: typer.Context) -> HealthCheckService:
    """Get health check service from typer context."""
    db_path = get_default_db_path()
    if ctx.parent and ctx.parent.params:
        db_path = Path(ctx.parent.params.get("db_path", str(get_default_db_path())))

    return get_health_check_service(db_path)


def _get_db_path_from_context(ctx: typer.Context) -> Path:
    """Get database path from typer context."""
    if ctx.parent and ctx.parent.params:
        return Path(ctx.parent.params.get("db_path", str(get_default_db_path())))
    return get_default_db_path()


@app.command()
def stats(
    ctx: typer.Context,
    slow_queries: bool = typer.Option(False, "--slow-queries", "-s", help="Show slow query log"),
    telemetry: bool = typer.Option(False, "--telemetry", "-t", help="Show telemetry stats"),
) -> None:
    """Show database statistics."""
    # Get health check service for stats
    health_service = _get_health_service_from_context(ctx)

    typer.echo("📊 Database Statistics")
    typer.echo("=" * 40)

    # Get database stats
    db_stats = health_service.get_stats()

    typer.echo(f"Observations:     {db_stats['observation_count']}")
    typer.echo(f"FTS Entries:     {db_stats['fts_count']}")
    typer.echo(f"Database Size:   {db_stats['db_size_human']}")

    # Show telemetry stats if requested
    if telemetry:
        typer.echo("\n📈 Telemetry Statistics (Last 24h)")
        typer.echo("-" * 40)

        db_path = _get_db_path_from_context(ctx)
        telemetry_service = get_telemetry_service(db_path)

        if not telemetry_service.is_enabled:
            typer.echo("Telemetry: DISABLED")
        else:
            counts = telemetry_service.get_event_counts("24h")

            if not counts:
                typer.echo("No telemetry events recorded")
            else:
                # Show memory-specific events
                mem_saves = counts.get("memory.save", 0)
                mem_searches = counts.get("memory.search", 0)
                mem_deletes = counts.get("memory.delete", 0)

                typer.echo(f"Memory Saves:    {mem_saves}")
                typer.echo(f"Memory Searches: {mem_searches}")
                typer.echo(f"Memory Deletes:  {mem_deletes}")

                # Show total events
                total_events = sum(counts.values())
                typer.echo(f"\nTotal Events:    {total_events}")

    # Show slow queries if requested
    if slow_queries:
        typer.echo("\n📝 Slow Query Log")
        typer.echo("-" * 40)

        query_logger = get_query_logger()
        slow = query_logger.get_slow_queries()

        if not slow:
            typer.echo("No slow queries logged")
        else:
            typer.echo(f"Total slow queries: {len(slow)}")
            for i, sq in enumerate(slow[:10], 1):
                typer.echo(f"\n{i}. {sq['duration_ms']:.2f} ms")
                typer.echo(f"   Query: {sq['query'][:60]}...")


@app.command()
def clear_slow_queries() -> None:
    """Clear the slow query log."""
    query_logger = get_query_logger()
    query_logger.clear()
    typer.echo("✅ Slow query log cleared")
