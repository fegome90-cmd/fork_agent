"""List command for CLI."""

from __future__ import annotations

import typer

from src.application.use_cases.list_observations import ListObservations

app = typer.Typer()


@app.command()
def list_observations(
    ctx: typer.Context,
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    repo = ctx.obj
    use_case = ListObservations(repo)
    results = use_case.execute(limit=limit)

    if not results:
        typer.echo("No observations found")
        return

    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")
