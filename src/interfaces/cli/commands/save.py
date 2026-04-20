"""Save command for CLI."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

import typer

from src.domain.entities.observation import Observation
from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer()


def _detect_git_project() -> str | None:
    """Try to detect project name from git remote origin."""
    try:
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        git = GitCommandExecutor()
        return git.detect_project_from_remote()
    except Exception:
        return None


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
    MANUAL = "manual"


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current: Any = ctx
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
    title: str | None = typer.Option(
        None, "--title", "-T", help="Optional title for the observation"
    ),
) -> None:
    """Save an observation to memory.

    Supports both legacy JSON metadata and structured fields for Engram parity.
    Structured fields automatically populate the metadata dictionary.
    """
    memory_service = ctx.obj

    # Validate content
    if not content or not content.strip():
        typer.echo("Error: Content cannot be empty", err=True)
        raise typer.Exit(1)  # noqa: B904
    # Null bytes are silently truncated by SQLite — reject early (RIPPER-001/002)
    if "\x00" in content:
        typer.echo("Error: content must not contain null bytes", err=True)
        raise typer.Exit(1)
    # Path traversal in topic_key (RIPPER-008)
    if topic_key is not None and (".." in topic_key):
        typer.echo("Error: topic_key must not contain path traversal patterns (..)", err=True)
        raise typer.Exit(1)
    # Build metadata from structured fields
    meta_dict: dict[str, Any] = {}

    # Parse legacy metadata if provided
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            typer.echo("Error: Invalid JSON metadata", err=True)
            raise typer.Exit(1) from None

    # Extract entity fields from metadata JSON (BUG-8/BUG-9)
    # Always pop to avoid duplication; CLI flags take precedence
    extracted_type = meta_dict.pop("type", None)
    if extracted_type is not None and obs_type is None:
        if isinstance(extracted_type, str) and extracted_type in Observation._ALLOWED_TYPES:
            obs_type = ObservationType(extracted_type)
        else:
            typer.echo(
                f"Error: Invalid type '{extracted_type}'. "
                f"Allowed: {sorted(Observation._ALLOWED_TYPES)}",
                err=True,
            )
            raise typer.Exit(1)  # noqa: B904
    extracted_topic = meta_dict.pop("topic_key", None)
    if extracted_topic is not None and topic_key is None:
        topic_key = extracted_topic

    extracted_project = meta_dict.pop("project", None)
    if extracted_project is not None and project is None:
        project = extracted_project

    # Auto-detect project from git remote if not provided
    if project is None:
        try:
            detected = _detect_git_project()
            if detected is not None:
                project = detected
        except Exception:
            pass

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

    try:
        observation = memory_service.save(
            content=content,
            metadata=meta_dict if meta_dict else None,
            topic_key=topic_key,
            project=project,
            type=obs_type.value if obs_type else None,
            title=title,
        )
        typer.echo(f"Saved: {observation.id}")
    except (ValueError, TypeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)  # noqa: B904
    # Flush telemetry to ensure events are persisted
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()
