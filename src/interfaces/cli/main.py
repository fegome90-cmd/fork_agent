"""Memory CLI - Main entry point."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import typer

from src.application.services.orchestration.events import SessionStartEvent
from src.interfaces.cli.commands import context, delete, get, list, save, search, stats, update
from src.interfaces.cli.commands.cleanup import cleanup
from src.interfaces.cli.commands.compact import app as compact_app
from src.interfaces.cli.commands.health import health
from src.interfaces.cli.commands.query import app as query_app
from src.interfaces.cli.commands.schedule import app as schedule_app
from src.interfaces.cli.commands.session import app as session_app
from src.interfaces.cli.commands.telemetry import app as telemetry_app
from src.interfaces.cli.dependencies import (
    get_hook_service,
    get_memory_service,
    get_telemetry_service,
)

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="memory",
    help="Manage agent memory observations",
)

app.command(name="save")(save.save)
app.command(name="search")(search.search)
app.command(name="list")(list.list_observations)
app.command(name="get")(get.get)
app.command(name="delete")(delete.delete)

app.command(name="update")(update.update)
app.command(name="context")(context.context)

app.command(name="cleanup")(cleanup)

app.command(name="health")(health)

app.add_typer(schedule_app, name="schedule")
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(query_app, name="query")
app.add_typer(session_app, name="session")
app.add_typer(compact_app, name="compact")

app.command(name="stats")(stats.stats)
app.command(name="clear-slow-queries")(stats.clear_slow_queries)


@app.callback()
def main(
    ctx: typer.Context,
    db_path: str = typer.Option(
        "data/memory.db",
        "--db",
        "-d",
        help="Path to memory database",
    ),
) -> None:
    ctx.obj = get_memory_service(Path(db_path))

    # Initialize telemetry session
    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    telemetry = get_telemetry_service(Path(db_path))
    if telemetry.is_enabled and not telemetry.session_id:
        telemetry.start_session(session_id=session_id)

    # Dispatch session start event using the shared singleton to avoid duplicate hooks.json parsing
    try:
        get_hook_service().dispatch(SessionStartEvent(session_id=session_id))
    except Exception as e:
        logger.debug("Hook dispatch failed [session_start]: %s", e)


if __name__ == "__main__":
    app()
