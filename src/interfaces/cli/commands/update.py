"""Update command for CLI."""

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
        if hasattr(current, "params") and "db_path" in current.params:
            return Path(current.params["db_path"])
        current = current.parent if hasattr(current, "parent") else None
    return None


@app.command()
def update(
    ctx: typer.Context,
    observation_id: str = typer.Argument(..., help="Full ID or prefix of the observation"),
    content: str | None = typer.Option(None, "--content", "-c", help="New content"),
    metadata: str | None = typer.Option(None, "--metadata", "-m", help="New JSON metadata"),
    obs_type: str | None = typer.Option(None, "--type", "-t", help="Observation type"),
    topic_key: str | None = typer.Option(None, "--topic-key", "-k", help="Topic key"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project name"),
) -> None:
    """Update an existing observation's content or metadata."""
    memory_service = ctx.obj
    meta_dict = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            typer.echo("Error: Invalid JSON metadata", err=True)
            raise typer.Exit(1)

    if (
        content is None
        and meta_dict is None
        and obs_type is None
        and topic_key is None
        and project is None
    ):
        typer.echo(
            "Error: At least one of --content, --metadata, --type, --topic-key, or --project must be provided",
            err=True,
        )
        raise typer.Exit(1)

    try:
        observation = memory_service.update(
            observation_id=observation_id,
            content=content,
            metadata=meta_dict,
            type=obs_type,
            topic_key=topic_key,
            project=project,
        )
        typer.echo(f"Updated: {observation.id} (Revision: {observation.revision_count})")

        # Flush telemetry
        db_path = _get_db_path_from_context(ctx)
        if db_path:
            telemetry = get_telemetry_service(db_path)
            telemetry.flush()
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
