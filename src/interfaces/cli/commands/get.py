"""Get command for CLI."""

from __future__ import annotations

import json
import os

import typer

from src.application.exceptions import ObservationNotFoundError
from src.interfaces.cli.commands._resolve_id import resolve_observation_id

app = typer.Typer()


@app.command()
def get(
    ctx: typer.Context,
    observation_id: str = typer.Argument(...),
) -> None:
    memory_service = ctx.obj

    # Hybrid dispatch: route through MCP when FORK_HYBRID=1 and server available
    if os.environ.get("FORK_HYBRID") == "1":
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(memory_service)
        obs, _receipt = dispatcher.dispatch_get(id=observation_id)
    else:
        try:
            obs = resolve_observation_id(memory_service, observation_id)
        except ObservationNotFoundError:
            typer.echo(f"Observation not found: {observation_id}", err=True)
            raise typer.Exit(1) from None
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
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
