"""Context command for CLI — quick retrieval of recent session summaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer

from src.interfaces.cli.dependencies import get_telemetry_service

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
def context(
    ctx: typer.Context,
    limit: int = typer.Option(5, "--limit", "-l", help="Max observations to return"),
    type: str | None = typer.Option(
        None, "--type", "-t", help="Filter by type (default: show all)"
    ),
) -> None:
    """Show recent context — session summaries and relevant observations."""
    memory_service = ctx.obj

    # Hybrid dispatch: route through MCP when FORK_HYBRID=1 and server available
    if os.environ.get("FORK_HYBRID") == "1":
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(memory_service)
        results, _receipt = dispatcher.dispatch_context(
            limit=limit, type=type, project=Path(os.getcwd()).name
        )
    else:
        # If type specified, filter by it; otherwise show recent
        results = memory_service.get_recent(limit=limit, type=type)

        # If no results with type filter, fallback to unfiltered
        if not results and type:
            results = memory_service.get_recent(limit=limit)

    if not results:
        typer.echo("No context found")
        return

    for obs in results:
        type_label = obs.type or "unknown"
        topic = obs.topic_key or ""
        prefix = f"({type_label})" if type_label != "unknown" else ""
        tag = f"[{topic}] " if topic else ""
        content_preview = obs.content[:180].replace("\n", " ")
        parts = f"[{obs.id[:8]}] {prefix}{tag}{content_preview}"
        typer.echo(parts)

    # Flush telemetry
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()
