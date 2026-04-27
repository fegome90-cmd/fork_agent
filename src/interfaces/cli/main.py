"""Memory CLI - Main entry point.

Uses deferred command registration to reduce cold-start time. Command modules
and heavy infrastructure imports are loaded on first CLI invocation, not at
import time. This saves ~90ms of cold-start overhead.
"""

from __future__ import annotations

import logging
import types
from pathlib import Path
from typing import Any

import click
import typer

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="memory",
    help="Manage agent memory observations",
)

# Module-level lazy imports via __getattr__ (PEP 562).
# These exist for backward compatibility with tests that patch this module.
# Frozen via MappingProxyType to prevent runtime mutation (defence in depth).
_LAZY_IMPORTS = types.MappingProxyType(
    {
        "get_memory_service": "src.infrastructure.persistence.container",
        "get_telemetry_service": "src.interfaces.cli.dependencies",
        "get_hook_service": "src.interfaces.cli.dependencies",
    }
)


def __getattr__(name: str) -> Any:
    """Lazy module-level attribute access for test patching compatibility."""
    if name in _LAZY_IMPORTS:
        mod = __import__(_LAZY_IMPORTS[name], fromlist=[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Advertise lazy exports for dir() and IDE autocomplete."""
    return list(globals()) + list(_LAZY_IMPORTS)


_commands_registered = False


def _register_commands() -> None:
    """Register all commands. Called once on first CLI invocation.

    Guards against double registration to support both the _LazyCLI proxy
    and direct test invocation (main._register_commands()).
    """
    global _commands_registered
    if _commands_registered:
        return

    from src.interfaces.cli.commands import (
        context,
        delete,
        diff,
        get,
        list,
        mcp,
        retrieve,
        save,
        search,
        stats,
        tui,
        update,
    )
    from src.interfaces.cli.commands.cleanup import cleanup
    from src.interfaces.cli.commands.compact import app as compact_app
    from src.interfaces.cli.commands.export import app as export_app
    from src.interfaces.cli.commands.health import health
    from src.interfaces.cli.commands.import_ import app as import_app
    from src.interfaces.cli.commands.launch import app as launch_app
    from src.interfaces.cli.commands.message import app as message_app
    from src.interfaces.cli.commands.project import app as project_app
    from src.interfaces.cli.commands.prompt import app as prompt_app
    from src.interfaces.cli.commands.query import app as query_app
    from src.interfaces.cli.commands.schedule import app as schedule_app
    from src.interfaces.cli.commands.session import app as session_app
    from src.interfaces.cli.commands.sync import app as sync_app
    from src.interfaces.cli.commands.telemetry import app as telemetry_app
    from src.interfaces.cli.commands.workflow import app as workflow_app

    app.command(name="save")(save.save)
    app.command(
        name="search", help="Full-text search using FTS5. Returns observations ranked by relevance."
    )(search.search)
    app.command(name="retrieve")(retrieve.retrieve)
    app.command(name="list", help="List recent observations in reverse chronological order.")(
        list.list_observations
    )
    app.command(name="get", help="Get a single observation by ID (accepts 8+ char prefix).")(
        get.get
    )
    app.command(name="delete")(delete.delete)
    app.command(name="diff")(diff.diff)
    app.command(name="update")(update.update)
    app.command(name="context")(context.context)
    app.command(name="cleanup")(cleanup)
    app.command(name="health")(health)
    app.command(name="stats")(stats.stats)
    app.command(name="clear-slow-queries")(stats.clear_slow_queries)
    app.command(name="tui")(tui.launch)

    app.add_typer(schedule_app, name="schedule")
    app.add_typer(telemetry_app, name="telemetry")
    app.add_typer(query_app, name="query")
    app.add_typer(session_app, name="session")
    app.add_typer(sync_app, name="sync")
    app.add_typer(compact_app, name="compact")
    app.add_typer(mcp.app, name="mcp")
    app.add_typer(project_app, name="project")
    app.add_typer(prompt_app, name="prompt")
    app.add_typer(export_app, name="export")
    app.add_typer(import_app, name="import")
    app.add_typer(workflow_app, name="workflow")
    app.add_typer(launch_app, name="launch")
    app.add_typer(message_app, name="message")

    # Mark registered only after all imports and registrations succeed.
    # If any import fails, the guard stays False and retry is possible.
    _commands_registered = True


def _get_default_db() -> str:
    """Lazy default -- only imports container when Typer reads the default."""
    from src.infrastructure.persistence.container import get_default_db_path

    return str(get_default_db_path())


def _get_services(db_path: Path) -> tuple[Any, Any, Any]:
    """Import and create services on demand. Defers heavy imports to callback."""
    # Use module-level __getattr__ resolution so test patches work correctly.
    # These trigger PEP 562 lazy imports on first access.
    from src.interfaces.cli import main as _self

    return (
        _self.get_memory_service(db_path),
        _self.get_telemetry_service(db_path),
        _self.get_hook_service(),
    )


@app.callback()
def main(
    ctx: typer.Context,
    db_path: str = typer.Option(
        _get_default_db,
        "--db",
        "-d",
        help="Path to memory database (default: XDG-compliant, env: FORK_MEMORY_DB)",
    ),
) -> None:
    """Manage agent memory observations."""
    # Skip heavy initialization for --help, --version, shell completion
    if ctx.resilient_parsing:
        return

    import uuid

    from src.application.services.orchestration.events import SessionStartEvent

    resolved = Path(db_path)
    service, telemetry, hook_service = _get_services(resolved)
    ctx.obj = service

    # Initialize telemetry session
    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    if telemetry.is_enabled and not telemetry.session_id:
        telemetry.start_session(session_id=session_id)

    # Dispatch session start event
    try:
        hook_service.dispatch(SessionStartEvent(session_id=session_id))
    except Exception as e:
        logger.debug("Hook dispatch failed [session_start]: %s", e)


def _build_cli() -> click.Command:
    """Build the final Click command with all sub-apps including Click-based workspace."""
    _register_commands()
    click_app = typer.main.get_command(app)
    if isinstance(click_app, click.Group):
        from src.interfaces.cli.workspace_commands import workspace as workspace_click_group

        click_app.add_command(workspace_click_group, name="workspace")
    return click_app


class _LazyCLI:
    """Proxy that builds the real CLI on first invocation."""

    def __init__(self) -> None:
        self._cli: click.Command | None = None

    def _ensure_cli(self) -> click.Command:
        if self._cli is None:
            self._cli = _build_cli()
        return self._cli

    def __call__(self, *args: object, **kwargs: object) -> object:
        return self._ensure_cli()(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._ensure_cli(), name)


cli = _LazyCLI()


if __name__ == "__main__":
    cli()
