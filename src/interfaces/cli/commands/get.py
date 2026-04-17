"""Get command for CLI."""

from __future__ import annotations

import json

import typer

app = typer.Typer()


@app.command()
def get(
    ctx: typer.Context,
    observation_id: str = typer.Argument(...),
) -> None:
    memory_service = ctx.obj

    try:
        obs = memory_service.get_by_id(observation_id)
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
    except Exception:
        typer.echo(f"Observation not found: {observation_id}", err=True)
        raise
