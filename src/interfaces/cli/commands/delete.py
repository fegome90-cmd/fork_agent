"""Delete command for CLI."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from src.interfaces.cli.commands._resolve_id import resolve_observation_id
from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer()


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            return Path(current.params["db_path"])
        current = current.parent if hasattr(current, "parent") else None
    return None


@app.command()
def delete(
    ctx: typer.Context,
    observation_id: str = typer.Argument(..., help="Full ID or prefix of the observation"),
    force: bool = typer.Option(False, "--force", "-f"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Verify observation belongs to project"
    ),
) -> None:
    memory_service = ctx.obj
    if not force and not typer.confirm(f"Delete observation {observation_id}?"):
        typer.echo("Cancelled")
        raise typer.Exit(0)  # noqa: B904
    try:
        resolved = resolve_observation_id(memory_service, observation_id)
        actual_id = resolved.id
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)  # noqa: B904
    # Verify project ownership if --project given or auto-detected
    # When --force is set, skip the project ownership check entirely
    if not force:
        effective_project = project if project is not None else Path(os.getcwd()).name
        if resolved.project and resolved.project != effective_project:
            typer.echo(
                f"Error: Observation belongs to project '{resolved.project}', "
                f"not '{effective_project}'. Use --force to override.",
                err=True,
            )
            raise typer.Exit(1)  # noqa: B904
    try:
        memory_service.delete(actual_id)
        typer.echo(f"Deleted: {actual_id}")

        # Flush telemetry to ensure events are persisted
        db_path = _get_db_path_from_context(ctx)
        if db_path:
            telemetry = get_telemetry_service(db_path)
            telemetry.flush()
    except Exception:
        raise
