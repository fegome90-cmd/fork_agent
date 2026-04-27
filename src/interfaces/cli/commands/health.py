"""Health check command for CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from src.infrastructure.persistence.container import get_default_db_path
from src.infrastructure.persistence.health_check import HealthCheckService
from src.interfaces.cli.dependencies import get_health_check_service

app = typer.Typer()

DEFAULT_DB_PATH = get_default_db_path()


def _get_health_service_from_context(ctx: typer.Context) -> HealthCheckService:
    """Get health check service from typer context."""
    db_path = get_default_db_path()
    if ctx.parent and ctx.parent.params:
        db_path = Path(ctx.parent.params.get("db_path", str(get_default_db_path())))

    return get_health_check_service(db_path)  # type: ignore[no-any-return]


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

    # Trifecta graph health
    try:
        import json as json_mod
        import subprocess

        repo_path = Path.cwd()
        result_trifecta = subprocess.run(
            ["trifecta", "graph", "status", "-s", str(repo_path), "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result_trifecta.returncode == 0:
            graph_data = json_mod.loads(result_trifecta.stdout)
            node_count = graph_data.get("node_count", 0)
            edge_count = graph_data.get("edge_count", 0)
            last_indexed = graph_data.get("last_indexed_at", "never")
            graph_exists = graph_data.get("exists", False)

            if graph_exists and node_count > 0:
                staleness = ""
                if last_indexed and last_indexed != "never":
                    from datetime import UTC, datetime

                    try:
                        indexed_time = datetime.fromisoformat(
                            last_indexed.replace("Z", "+00:00"),
                        )
                        age_hours = (datetime.now(UTC) - indexed_time).total_seconds() / 3600
                        if age_hours < 1:
                            staleness = f"{int(age_hours * 60)}m ago (fresh)"
                        elif age_hours < 24:
                            staleness = f"{int(age_hours)}h ago (fresh)"
                        else:
                            staleness = f"{int(age_hours)}h ago (STALE)"
                    except Exception:
                        staleness = last_indexed

                typer.echo(
                    f"Trifecta Graph:          {node_count} nodes, {edge_count} edges | {staleness}",
                )
            else:
                typer.echo("Trifecta Graph:          not initialized")
        else:
            typer.echo("Trifecta Graph:          CLI not available")
    except FileNotFoundError:
        typer.echo("Trifecta Graph:          CLI not found")
    except Exception:
        typer.echo("Trifecta Graph:          check failed")

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
