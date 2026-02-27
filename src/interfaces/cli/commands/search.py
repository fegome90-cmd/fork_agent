"""Search command for CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer()


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
) -> None:
    memory_service = ctx.obj
    results = memory_service.search(query=query, limit=limit)

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
