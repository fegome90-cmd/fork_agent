"""List command for CLI."""

from __future__ import annotations

import os
from pathlib import Path

import typer

app = typer.Typer()


def _auto_detect_project() -> str | None:
    """Auto-detect project name from CWD basename."""
    return Path(os.getcwd()).name


def _should_auto_detect(ctx: typer.Context) -> bool:
    """Skip auto-detect when --db is explicitly provided (test/isolated DB)."""
    # db_path is on the main app callback, not the subcommand
    db_path = None
    parent = getattr(ctx, "parent", None)
    if parent and hasattr(parent, "params"):
        db_path = parent.params.get("db_path")
    if db_path is None:
        db_path = ctx.params.get("db_path")
    default_db = str(Path(os.getcwd()) / "data" / "memory.db")
    return db_path is None or str(db_path) == default_db


@app.command()
def list_observations(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of observations to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of observations to skip"),
    obs_type: str | None = typer.Option(None, "--type", "-t", help="Filter by observation type"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Filter by project (auto-detected from CWD)"
    ),
) -> None:
    memory_service = ctx.obj
    if offset < 0:
        typer.echo("Error: offset must be >= 0", err=True)
        raise typer.Exit(1)
    if limit < 0:
        typer.echo("Error: limit must be >= 0", err=True)
        raise typer.Exit(1)
    effective_project = (
        project
        if project is not None
        else (_auto_detect_project() if _should_auto_detect(ctx) else None)
    )
    if project is None and effective_project is not None:
        typer.echo(
            f"Note: Auto-filtering by project '{effective_project}' (use --project to override, or --project '' for all)",
            err=True,
        )
    results = memory_service.get_recent(
        limit=limit, offset=offset, type=obs_type, project=effective_project
    )

    if not results:
        typer.echo("No observations found")
        return

    typer.echo(f"Showing {len(results)} observations (offset: {offset})")
    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")
