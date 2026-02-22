"""Search command for CLI."""

from __future__ import annotations

import typer

from src.application.use_cases.search_observations import SearchObservations

app = typer.Typer()


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(...),
    limit: int | None = typer.Option(None, "--limit", "-l"),
) -> None:
    repo = ctx.obj
    use_case = SearchObservations(repo)
    results = use_case.execute(query=query, limit=limit)

    if not results:
        typer.echo("No results found")
        return

    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")
