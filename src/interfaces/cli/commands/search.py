"""Search command for CLI."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer()


def _auto_detect_project() -> str | None:
    """Auto-detect project name from CWD basename."""
    return Path(os.getcwd()).name


def _should_auto_detect(ctx: typer.Context) -> bool:
    """Skip auto-detect when --db is explicitly provided (test/isolated DB)."""
    db_path = None
    parent = getattr(ctx, "parent", None)
    if parent and hasattr(parent, "params"):
        db_path = parent.params.get("db_path")
    if db_path is None:
        db_path = ctx.params.get("db_path")
    default_db = str(Path(os.getcwd()) / "data" / "memory.db")
    return db_path is None or str(db_path) == default_db


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current = ctx
    while current:
        if hasattr(current, 'params') and 'db_path' in current.params:
            return Path(current.params['db_path'])
        current = current.parent if hasattr(current, 'parent') else None
    return None


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(...),
    limit: int | None = typer.Option(None, "--limit", "-l"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project (auto-detected from CWD)"),
) -> None:
    memory_service = ctx.obj
    effective_project = project if project is not None else (_auto_detect_project() if _should_auto_detect(ctx) else None)
    results = memory_service.search(query=query, limit=limit, project=effective_project)

    if not results:
        typer.echo("No results found")
        return

    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")

    # Flush telemetry to ensure events are persisted
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()
