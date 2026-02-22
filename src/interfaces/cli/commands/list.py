"""List command for CLI."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.command()
def list_observations(
    ctx: typer.Context,
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    memory_service = ctx.obj
    results = memory_service.get_recent(limit=limit)

    if not results:
        typer.echo("No observations found")
        return

    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")
