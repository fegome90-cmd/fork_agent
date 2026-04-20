"""Retrieve command — enhanced multi-signal search using pipeline v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from src.infrastructure.persistence.container import get_repository
from src.infrastructure.retrieval.v2.enhanced_search import EnhancedRetrievalSearchService

app = typer.Typer()


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current: Any = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            return Path(current.params["db_path"])
        current = current.parent if hasattr(current, "parent") else None
    return None


@app.command()
def retrieve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query for enhanced retrieval"),
    limit: int | None = typer.Option(None, "--limit", "-l", help="Max results (default: 5)"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    type: str | None = typer.Option(None, "--type", "-t", help="Filter by observation type"),
) -> None:
    """Enhanced retrieval search with multi-signal scoring.

    Uses concept extraction, semantic bridges, and keyword density
    to produce more relevant results than basic FTS5 search.
    """
    if limit is not None and limit <= 0:
        typer.echo("Error: limit must be a positive integer", err=True)
        raise typer.Exit(1)

    db_path = _get_db_path_from_context(ctx)
    repository = get_repository(db_path)
    service = EnhancedRetrievalSearchService(repository)  # type: ignore[arg-type]
    results = service.search(query=query, limit=limit, project=project, type=type)

    if not results:
        typer.echo("No results found")
        return

    for obs in results:
        typer.echo(f"[{obs.id[:8]}] {obs.content[:80]}...")
