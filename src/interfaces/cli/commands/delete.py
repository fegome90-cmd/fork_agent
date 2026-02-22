"""Delete command for CLI."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.command()
def delete(
    ctx: typer.Context,
    observation_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    memory_service = ctx.obj
    if not force:
        if not typer.confirm(f"Delete observation {observation_id}?"):
            typer.echo("Cancelled")
            raise typer.Exit(0)

    try:
        memory_service.delete(observation_id)
        typer.echo(f"Deleted: {observation_id}")
    except Exception:
        typer.echo(f"Observation not found: {observation_id}", err=True)
        raise typer.Exit(1)
