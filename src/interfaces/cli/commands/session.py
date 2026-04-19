"""Session commands for CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from src.application.services.session_service import SessionService

app = typer.Typer()


def _get_session_service(db_path: Path | None = None) -> SessionService:
    from src.infrastructure.persistence.container import get_session_service
    return get_session_service(db_path)


@app.command()
def start(
    ctx: typer.Context,
    project: str = typer.Option(None, "--project", "-p", help="Project name (auto-detected if not provided)"),
    goal: str = typer.Option(None, "--goal", "-g", help="Session goal/description"),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="Session instructions/constraints"
    ),
) -> None:
    """Start a new session."""
    import os

    service = _get_session_service()
    directory = os.getcwd()
    proj = project or Path(directory).name

    session = service.start_session(
        project=proj,
        directory=directory,
        goal=goal,
        instructions=instructions,
    )

    typer.echo(f"Session started: {session.id}")
    typer.echo(f"  Project: {session.project}")
    typer.echo(f"  Directory: {session.directory}")
    if session.goal:
        typer.echo(f"  Goal: {session.goal}")


@app.command()
def end(
    ctx: typer.Context,
    summary: str = typer.Option(None, "--summary", "-s", help="Summary of what was accomplished"),
    project: str = typer.Option(
        None, "--project", "-p", help="Project name (auto-detected if not provided)"
    ),
) -> None:
    """End the active session."""
    import os

    service = _get_session_service()

    # Auto-detect project from CWD when not explicitly provided (same as list/context)
    proj = project or Path(os.getcwd()).name

    active = service.get_active(proj)
    if active is None:
        typer.echo("No active session found" + (f" for project: {proj}" if proj else ""), err=True)
        raise typer.Exit(1)

    session = service.end_session(active.id, summary)

    typer.echo(f"Session ended: {session.id}")
    typer.echo(f"  Duration: {_format_duration(session.duration_ms())}")
    if session.summary:
        typer.echo(f"  Summary: {session.summary}")


@app.command()
def list(
    ctx: typer.Context,
    project: str = typer.Option(
        None, "--project", "-p", help="Project name (auto-detected if not provided)"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of sessions to show"),
) -> None:
    """List recent sessions."""
    import os
    from datetime import datetime

    service = _get_session_service()

    # Auto-detect project if not provided
    proj = project or Path(os.getcwd()).name

    sessions = service.list_sessions(proj, limit=limit)

    if not sessions:
        typer.echo(f"No sessions found for project: {proj}")
        return

    typer.echo(f"Recent sessions for '{proj}':\n")

    for session in sessions:
        status = "[active]" if session.is_active() else ""
        started = datetime.fromtimestamp(session.started_at / 1000)
        started_str = started.strftime("%Y-%m-%d %H:%M")

        typer.echo(f"  {session.id[:8]}... {started_str} {status}")
        if session.goal:
            typer.echo(f"           Goal: {session.goal[:60]}...")
        if session.summary:
            typer.echo(f"           Summary: {session.summary[:60]}...")
        typer.echo()


@app.command()
def context(
    ctx: typer.Context,
    project: str = typer.Option(
        None, "--project", "-p", help="Project name (auto-detected if not provided)"
    ),
    limit: int = typer.Option(3, "--limit", "-l", help="Number of sessions to show"),
) -> None:
    """Get recent sessions and their observations for recovery."""
    import os
    from datetime import datetime

    service = _get_session_service()

    # Auto-detect project if not provided
    proj = project or Path(os.getcwd()).name

    sessions = service.get_context(proj, limit=limit)

    if not sessions:
        typer.echo(f"No session context found for project: {proj}")
        return

    typer.echo(f"=== Session Context for '{proj}' ===\n")

    for i, session in enumerate(sessions, 1):
        status = "ACTIVE" if session.is_active() else "COMPLETED"
        started = datetime.fromtimestamp(session.started_at / 1000)
        typer.echo(f"[{i}] Session: {session.id[:8]}... [{status}]")
        typer.echo(f"    Started: {started.strftime('%Y-%m-%d %H:%M')}")
        typer.echo(f"    Directory: {session.directory}")

        if session.goal:
            typer.echo(f"    Goal: {session.goal}")
        if session.instructions:
            typer.echo(f"    Instructions: {session.instructions}")
        if session.summary:
            typer.echo(f"    Summary: {session.summary}")
        typer.echo()


def _format_duration(duration_ms: int | None) -> str:
    """Format duration in milliseconds to human-readable string."""
    if duration_ms is None:
        return "in progress"

    seconds = duration_ms // 1000
    minutes = seconds // 60
    hours = minutes // 60

    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    if minutes > 0:
        return f"{minutes}m {seconds % 60}s"
    return f"{seconds}s"
