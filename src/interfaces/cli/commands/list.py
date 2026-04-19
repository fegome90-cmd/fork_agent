"""List command for CLI."""

from __future__ import annotations

import os
from pathlib import Path

import typer

app = typer.Typer()


def _auto_detect_project() -> str | None:
    """Auto-detect project name from CWD basename."""
    return Path(os.getcwd()).name


@app.command()
def list_observations(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of observations to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of observations to skip"),
    obs_type: str | None = typer.Option(None, "--type", "-t", help="Filter by observation type"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project (auto-detected from CWD)"),
) -> None:
    memory_service = ctx.obj
    effective_project = project if project is not None else _auto_detect_project()
    results = memory_service.get_recent(limit=limit, offset=offset, type=obs_type, project=effective_project)

    if not results:
        typer.echo("No observations found")
        return

    typer.echo(f"Showing {len(results)} observations (offset: {offset})")
    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")
