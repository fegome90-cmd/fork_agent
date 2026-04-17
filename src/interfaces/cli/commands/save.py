"""Save command for CLI."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

import typer

from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer()


class ObservationType(StrEnum):
    """Enumeration of observation types for structured saving."""

    DECISION = "decision"
    BUGFIX = "bugfix"
    DISCOVERY = "discovery"
    PATTERN = "pattern"
    CONFIG = "config"
    PREFERENCE = "preference"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"
    LEARNING = "learning"
    SESSION_SUMMARY = "session-summary"


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            return Path(current.params["db_path"])
        current = current.parent if hasattr(current, "parent") else None
    return None


@app.command()
def save(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="Observation content"),
    metadata: str | None = typer.Option(
        None, "--metadata", "-m", help="JSON metadata (legacy, use structured flags)"
    ),
    obs_type: ObservationType | None = typer.Option(
        None, "--type", "-t", help="Observation type for structured metadata"
    ),
    project: str | None = typer.Option(None, "--project", "-p", help="Override project name"),
    topic_key: str | None = typer.Option(None, "--topic-key", "-k", help="Topic key for upsert"),
    what: str | None = typer.Option(None, "--what", help="What was done (structured field)"),
    why: str | None = typer.Option(None, "--why", help="Why it matters (structured field)"),
    where: str | None = typer.Option(
        None, "--where", help="Where (files, components) (structured field)"
    ),
    learned: str | None = typer.Option(None, "--learned", help="Key takeaway (structured field)"),
) -> None:
    """Save an observation to memory.

    Supports both legacy JSON metadata and structured fields for Engram parity.
    Structured fields automatically populate the metadata dictionary.
    """
    memory_service = ctx.obj

    # Validate content
    if not content or not content.strip():
        typer.echo("Error: Content cannot be empty", err=True)
        raise typer.Exit(1)

    # Build metadata from structured fields
    meta_dict: dict[str, Any] = {}

    # Parse legacy metadata if provided
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            typer.echo("Error: Invalid JSON metadata", err=True)
            raise

    # Add structured fields as nested metadata (Engram parity)
    structured_fields = {}
    if what:
        structured_fields["what"] = what
    if why:
        structured_fields["why"] = why
    if where:
        structured_fields["where"] = where
    if learned:
        structured_fields["learned"] = learned

    if structured_fields:
        meta_dict["structured"] = structured_fields

    observation = memory_service.save(
        content=content,
        metadata=meta_dict if meta_dict else None,
        topic_key=topic_key,
        project=project,
        type=obs_type.value if obs_type else None,
    )
    typer.echo(f"Saved: {observation.id}")

    # Flush telemetry to ensure events are persisted
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()
