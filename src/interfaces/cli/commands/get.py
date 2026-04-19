"""Get command for CLI."""

from __future__ import annotations

import json

import typer

from src.application.exceptions import ObservationNotFoundError

app = typer.Typer()


@app.command()
def get(
    ctx: typer.Context,
    observation_id: str = typer.Argument(...),
) -> None:
    memory_service = ctx.obj

    obs = None
    try:
        obs = memory_service.get_by_id(observation_id)
    except ObservationNotFoundError:
        # Try short ID prefix match
        all_obs = memory_service._repository.get_all()
        matches = [o for o in all_obs if o.id.startswith(observation_id)]
        if len(matches) == 1:
            obs = matches[0]
        elif len(matches) > 1:
            typer.echo(f"Ambiguous ID '{observation_id}' matches {len(matches)} observations", err=True)
            raise typer.Exit(1) from None
        else:
            typer.echo(f"Observation not found: {observation_id}", err=True)
            raise typer.Exit(1) from None

    if obs is None:
        typer.echo(f"Observation not found: {observation_id}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"ID: {obs.id}")
    typer.echo(f"Timestamp: {obs.timestamp}")
    typer.echo(f"Content: {obs.content}")
    if obs.type:
        typer.echo(f"Type: {obs.type}")
    if obs.project:
        typer.echo(f"Project: {obs.project}")
    if obs.topic_key:
        typer.echo(f"Topic Key: {obs.topic_key}")
    if obs.session_id:
        typer.echo(f"Session ID: {obs.session_id}")
    typer.echo(f"Revision Count: {obs.revision_count}")
    if obs.metadata:
        typer.echo(f"Metadata: {json.dumps(obs.metadata, indent=2)}")
