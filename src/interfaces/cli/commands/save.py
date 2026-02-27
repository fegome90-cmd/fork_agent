"""Save command for CLI."""

from __future__ import annotations

import json
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
def save(
    ctx: typer.Context,
    content: str = typer.Argument(...),
    metadata: str | None = typer.Option(None, "--metadata", "-m"),
) -> None:
    memory_service = ctx.obj
    meta_dict = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            typer.echo("Error: Invalid JSON metadata", err=True)
            raise

    if not content or not content.strip():
        typer.echo("Error: Content cannot be empty", err=True)
        raise typer.Exit(1)

    observation = memory_service.save(content=content, metadata=meta_dict)
    typer.echo(f"Saved: {observation.id}")

    # Flush telemetry to ensure events are persisted
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()
