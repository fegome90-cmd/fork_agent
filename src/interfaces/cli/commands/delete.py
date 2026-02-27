"""Delete command for CLI."""

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
def delete(
    ctx: typer.Context,
    observation_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    memory_service = ctx.obj
    if not force and not typer.confirm(f"Delete observation {observation_id}?"):
        typer.echo("Cancelled")
        raise typer.Exit(0)

    try:
        memory_service.delete(observation_id)
        typer.echo(f"Deleted: {observation_id}")

        # Flush telemetry to ensure events are persisted
        db_path = _get_db_path_from_context(ctx)
        if db_path:
            telemetry = get_telemetry_service(db_path)
            telemetry.flush()
    except Exception:
        typer.echo(f"Observation not found: {observation_id}", err=True)
        raise
