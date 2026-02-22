"""Save command for CLI."""

from __future__ import annotations

import json

import typer

app = typer.Typer()


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
            raise typer.Exit(1)

    if not content or not content.strip():
        typer.echo("Error: Content cannot be empty", err=True)
        raise typer.Exit(1)

    observation = memory_service.save(content=content, metadata=meta_dict)
    typer.echo(f"Saved: {observation.id}")
