"""Diff command for CLI — compare observations between references."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from src.application.services.diff_service import DiffService

app = typer.Typer()


def _auto_detect_project() -> str | None:
    """Auto-detect project name from CWD basename."""
    return Path(os.getcwd()).name


def _should_auto_detect(ctx: typer.Context) -> bool:
    """Skip auto-detect when --db is explicitly provided (test/isolated DB)."""
    db_path = None
    parent = getattr(ctx, "parent", None)
    if parent and hasattr(parent, "params"):
        db_path = parent.params.get("db_path")
    if db_path is None:
        db_path = ctx.params.get("db_path")
    default_db = str(Path(os.getcwd()) / "data" / "memory.db")
    return db_path is None or str(db_path) == default_db


def _get_diff_service(ctx: typer.Context) -> DiffService:
    """Create a DiffService from the CLI context."""
    from src.application.services.diff_service import DiffService

    # Get db_path from context to create an isolated service
    db_path = None
    current: typer.Context | None = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            db_path = current.params["db_path"]
            break
        current = getattr(current, "parent", None)

    if db_path:
        from src.infrastructure.persistence.container import get_repository

        repo = get_repository(Path(db_path))
    else:
        memory_service = ctx.obj
        repo = memory_service._repository

    return DiffService(repo)


def _parse_timestamp(value: str) -> int:
    """Parse a timestamp string to Unix ms. Supports relative offsets like -1h, -30m."""
    if value.startswith("-"):
        import time

        suffix = value[1:]
        now = int(time.time() * 1000)
        if suffix.endswith("h"):
            hours = int(suffix[:-1])
            return now - hours * 3_600_000
        if suffix.endswith("m"):
            minutes = int(suffix[:-1])
            return now - minutes * 60_000
        if suffix.endswith("d"):
            days = int(suffix[:-1])
            return now - days * 86_400_000
        if suffix.endswith("s"):
            seconds = int(suffix[:-1])
            return now - seconds * 1_000
        raise ValueError(f"Unknown relative offset format: {value}")
    try:
        ts = int(value)
        if ts < 0:
            raise ValueError("Timestamp must be non-negative")
        return ts
    except ValueError:
        raise ValueError(
            f"Invalid timestamp: {value} (expected Unix ms or relative like -1h)"
        ) from None


def _resolve_project(ctx: typer.Context, project: str | None) -> str | None:
    """Resolve project from explicit arg or auto-detect."""
    if project is not None:
        return project
    if _should_auto_detect(ctx):
        detected = _auto_detect_project()
        if detected:
            typer.echo(
                f"Note: Auto-filtering by project '{detected}' (use --project to override)",
                err=True,
            )
            return detected
    return None


@app.command()
def diff(
    ctx: typer.Context,
    ref_a: str = typer.Argument(None, help="First reference (observation ID)"),
    ref_b: str = typer.Argument(None, help="Second reference (observation ID)"),
    before: str = typer.Option(None, "--before", help="Reference window end timestamp"),
    after: str = typer.Option(None, "--after", help="Target window start timestamp"),
    session: list[str] = typer.Option([], "--session", help="Session IDs (provide exactly 2)"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    obs_type: str | None = typer.Option(None, "--type", "-t", help="Filter by observation type"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Compare observations between two references.

    Supports three modes:
    - By ID: memory diff <id1> <id2>
    - By session: memory diff --session <s1> --session <s2>
    - By timestamp: memory diff --before <ts> --after <ts>
    """
    from src.application.services.diff_formatter import DiffFormatter

    # Validate mutual exclusivity
    has_ids = ref_a is not None or ref_b is not None
    has_sessions = len(session) > 0
    has_timestamps = before is not None or after is not None

    if has_ids and has_sessions:
        typer.echo("Error: Cannot use observation IDs with --session", err=True)
        raise typer.Exit(1)
    if has_ids and has_timestamps:
        typer.echo("Error: Cannot use observation IDs with --before/--after", err=True)
        raise typer.Exit(1)
    if has_sessions and has_timestamps:
        typer.echo("Error: Cannot use --session with --before/--after", err=True)
        raise typer.Exit(1)

    if not has_ids and not has_sessions and not has_timestamps:
        typer.echo(
            "Error: Provide either two observation IDs, two --session flags, or --before/--after",
            err=True,
        )
        raise typer.Exit(1)

    if format not in ("text", "json"):
        typer.echo(f"Error: unknown format '{format}' (expected: text, json)", err=True)
        raise typer.Exit(1)

    try:
        svc = _get_diff_service(ctx)
    except Exception as e:
        typer.echo(f"Error: Failed to initialize diff service: {e}", err=True)
        raise typer.Exit(1) from e

    effective_project = _resolve_project(ctx, project)

    try:
        if has_ids:
            if ref_a is None or ref_b is None:
                typer.echo("Error: Two observation IDs required for ID diff", err=True)
                raise typer.Exit(1)
            result = svc.diff_by_id(ref_a, ref_b)

        elif has_sessions:
            if len(session) != 2:
                typer.echo("Error: Exactly 2 --session values required", err=True)
                raise typer.Exit(1)
            result = svc.diff_by_session(
                session[0],
                session[1],
                project=effective_project,
                obs_type=obs_type,
            )

        else:  # timestamps
            if before is None or after is None:
                typer.echo("Error: Both --before and --after required for timestamp diff", err=True)
                raise typer.Exit(1)
            try:
                before_ms = _parse_timestamp(before)
            except ValueError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1) from e
            try:
                after_ms = _parse_timestamp(after)
            except ValueError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1) from e
            if before_ms >= after_ms:
                typer.echo("Error: --before must be before --after", err=True)
                raise typer.Exit(1)
            result = svc.diff_by_timestamp(
                before=(0, before_ms),
                after=(before_ms + 1, after_ms),
                project=effective_project,
                obs_type=obs_type,
            )

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        # Handle ObservationNotFoundError and similar
        err_msg = str(e)
        if "not found" in err_msg.lower():
            typer.echo(f"Error: {e}", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    if format == "json":
        typer.echo(DiffFormatter.format_json(result))
    else:
        typer.echo(DiffFormatter.format_text(result))
