"""Health check command for CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from src.infrastructure.persistence.health_check import HealthCheckService
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
def health(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    fix: bool = typer.Option(False, "--fix", "-f", help="Attempt to fix FTS desync"),
) -> None:
    """Check database health and integrity.

    Performs integrity checks and reports on database health.
    """
    health_service = _get_health_service_from_context(ctx)

    typer.echo("🔍 Running health checks...")
    typer.echo("-" * 40)

    result = health_service.check_health(verbose=verbose)

    # Display results
    typer.echo(f"Database Integrity:     {'✅ OK' if result.integrity_ok else '❌ FAILED'}")
    typer.echo(f"FTS Index Sync:         {'✅ SYNCED' if result.fts_synced else '❌ DESYNCED'}")
    typer.echo(f"Observations:           {result.observation_count}")
    typer.echo(f"FTS Entries:            {result.fts_count}")
    typer.echo(f"Database Size:          {result.db_size_bytes:,} bytes")

    if result.issues:
        typer.echo("\n⚠️  Issues found:")
        for issue in result.issues:
            typer.echo(f"  - {issue}")
    else:
        typer.echo("\n✅ Database is healthy!")

    # Fix FTS if requested
    if fix and not result.fts_synced:
        typer.echo("\n🔧 Repairing FTS index...")
        try:
            rebuilt = health_service.repair_fts()
            typer.echo(f"✅ Rebuilt {rebuilt} FTS entries")

            # Recheck
            result = health_service.check_health()
            if result.fts_synced:
                typer.echo("✅ FTS index repaired successfully!")
            else:
                typer.echo("❌ FTS repair did not resolve the issue")
        except Exception as e:
            typer.echo(f"❌ Failed to repair FTS: {e}", err=True)

    # Exit with error code if unhealthy
    if not result.is_healthy:
        raise typer.Exit(code=1)
