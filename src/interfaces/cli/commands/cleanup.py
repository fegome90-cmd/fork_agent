"""Cleanup command for CLI."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from src.application.services.cleanup_service import CleanupService
from src.infrastructure.persistence.container import get_default_db_path
from src.interfaces.cli.dependencies import get_cleanup_service

app = typer.Typer()

DEFAULT_DB_PATH = get_default_db_path()


def _get_cleanup_service_from_context(ctx: typer.Context) -> CleanupService:
    """Get cleanup service from typer context.

    Prefers the injected service from ctx.obj if available,
    falls back to constructing from db_path otherwise.
    """
    # Try to get from injected context first
    if ctx.obj is not None and hasattr(ctx.obj, "cleanup_service"):
        return cast(CleanupService, ctx.obj.cleanup_service())

    # Fallback: construct from db_path
    db_path = get_default_db_path()
    if ctx.parent and ctx.parent.params:
        db_path = Path(ctx.parent.params.get("db_path", str(get_default_db_path())))

    return get_cleanup_service(db_path)


@app.command()
def cleanup(
    ctx: typer.Context,
    days: int = typer.Option(90, "--days", "-d", help="Delete observations older than N days"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only, don't delete"),
    vacuum: bool = typer.Option(
        False, "--vacuum", "-v", help="Run VACUUM after deletion to reclaim space"
    ),
    optimize_fts: bool = typer.Option(
        False, "--optimize-ft", "-o", help="Optimize FTS index after cleanup"
    ),
) -> None:
    """Clean up old observations from the database.

    By default, this runs in dry-run mode to preview what would be deleted.
    Use --no-dry-run to actually delete observations.
    """
    cleanup_service = _get_cleanup_service_from_context(ctx)

    if days <= 0:
        typer.echo("Error: days must be a positive integer", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"🔍 DRY RUN - Preview of observations older than {days} days:")
        typer.echo("-" * 50)

    result = cleanup_service.cleanup_old_observations(days=days, dry_run=dry_run)

    if dry_run:
        typer.echo(f"Would delete: {result.deleted_count} observations")
        typer.echo(f"Would delete from FTS: {result.fts_deleted_count} entries")
        typer.echo("\n💡 Run with --no-dry-run to actually delete.")
    else:
        typer.echo(f"✅ Deleted: {result.deleted_count} observations")
        typer.echo(f"✅ Deleted from FTS: {result.fts_deleted_count} entries")

        if vacuum:
            typer.echo("Running VACUUM to reclaim space...")
            cleanup_service.vacuum_database()
            typer.echo("✅ VACUUM complete")

        if optimize_fts:
            typer.echo("Optimizing FTS index...")
            cleanup_service.optimize_fts()
            typer.echo("✅ FTS optimization complete")
