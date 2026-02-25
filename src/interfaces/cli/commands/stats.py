"""Stats command for CLI - shows database statistics."""

from __future__ import annotations

from pathlib import Path

import typer

from src.infrastructure.persistence.health_check import HealthCheckService
from src.infrastructure.persistence.query_logger import get_query_logger
from src.interfaces.cli.dependencies import get_health_check_service

app = typer.Typer()

DEFAULT_DB_PATH = Path("data/memory.db")


def _get_health_service_from_context(ctx: typer.Context) -> HealthCheckService:
    """Get health check service from typer context."""
    db_path = DEFAULT_DB_PATH
    if ctx.parent and ctx.parent.params:
        db_path = Path(ctx.parent.params.get("db_path", DEFAULT_DB_PATH))

    return get_health_check_service(db_path)


@app.command()
def stats(
    ctx: typer.Context,
    slow_queries: bool = typer.Option(False, "--slow-queries", "-s", help="Show slow query log"),
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
