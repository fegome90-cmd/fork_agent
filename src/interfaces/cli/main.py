"""Memory CLI - Main entry point."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import typer

from src.application.services.orchestration.events import SessionStartEvent
from src.interfaces.cli.commands import delete, get, list, save, search
from src.interfaces.cli.commands.cleanup import cleanup
from src.interfaces.cli.commands.health import health
from src.interfaces.cli.commands import stats
from src.interfaces.cli.commands.schedule import app as schedule_app
from src.interfaces.cli.commands.workflow import app as workflow_app
from src.interfaces.cli.dependencies import get_hook_service, get_memory_service

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

app.command(name="cleanup")(cleanup)

app.command(name="health")(health)

app.add_typer(schedule_app, name="schedule")
app.add_typer(workflow_app, name="workflow")

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
    # Dispatch session start event using the shared singleton to avoid duplicate hooks.json parsing
    try:
        session_id = f"cli-{uuid.uuid4().hex[:8]}"
        get_hook_service().dispatch(SessionStartEvent(session_id=session_id))
    except Exception as e:
        logger.debug("Hook dispatch failed [session_start]: %s", e)


if __name__ == "__main__":
    app()
