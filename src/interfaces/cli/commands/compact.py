"""Compaction protocol commands for CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from src.interfaces.cli.dependencies import get_telemetry_service

app = typer.Typer()


def _get_db_path_from_context(ctx: typer.Context) -> Path | None:
    """Get database path from CLI context."""
    current = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            return Path(current.params["db_path"])
        current = current.parent if hasattr(current, "parent") else None
    return None


def _get_project_name(project: str | None = None) -> str:
    """Get project name from option or auto-detect from CWD."""
    import os

    if project:
        return project
    return Path(os.getcwd()).name


@app.command(name="save-summary")
def save_summary(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal", "-g", help="Session goal"),
    instructions: str | None = typer.Option(
        None, "--instructions", "-i", help="Session instructions"
    ),
    discoveries: str | None = typer.Option(
        None, "--discoveries", "-d", help="Key discoveries (comma-separated)"
    ),
    accomplished: str | None = typer.Option(
        None, "--accomplished", "-a", help="What was accomplished"
    ),
    next_steps: str | None = typer.Option(
        None, "--next-steps", "-n", help="Next steps"
    ),
    files: str | None = typer.Option(
        None, "--files", "-f", help="Relevant files (comma-separated)"
    ),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project name (auto-detected if not provided)"
    ),
) -> None:
    """Save a structured session summary to observations.

    Saves a session-summary observation with type="session-summary" and
    topic_key="compact/session-summary" for automatic recovery.
    """
    memory_service = ctx.obj
    proj = _get_project_name(project)

    # Build structured metadata
    structured: dict[str, Any] = {
        "goal": goal,
    }

    if instructions:
        structured["instructions"] = instructions
    if discoveries:
        structured["discoveries"] = [d.strip() for d in discoveries.split(",") if d.strip()]
    if accomplished:
        structured["accomplished"] = accomplished
    if next_steps:
        structured["next_steps"] = [s.strip() for s in next_steps.split(",") if s.strip()]
    if files:
        structured["files"] = [f.strip() for f in files.split(",") if f.strip()]

    # Build full metadata
    metadata: dict[str, Any] = {
        "type": "session-summary",
        "project": proj,
        "topic_key": "compact/session-summary",
        "structured": structured,
    }

    # Generate content from structured data
    content_parts = [f"Session Summary for {proj}", f"Goal: {goal}"]

    if accomplished:
        content_parts.append(f"Accomplished: {accomplished}")
    if discoveries:
        content_parts.append(f"Discoveries: {', '.join(structured.get('discoveries', []))}")
    if next_steps:
        content_parts.append(f"Next steps: {', '.join(structured.get('next_steps', []))}")

    content = "\n".join(content_parts)

    # Save as observation
    observation = memory_service.save(content=content, metadata=metadata)

    typer.echo(f"Session summary saved: {observation.id}")
    typer.echo(f"  Project: {proj}")
    typer.echo("  Topic: compact/session-summary")

    # Flush telemetry
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()


@app.command()
def recover(
    ctx: typer.Context,
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project name (auto-detected if not provided)"
    ),
    summary_limit: int = typer.Option(
        3, "--summary-limit", "-s", help="Number of session summaries to show"
    ),
    observation_limit: int = typer.Option(
        10, "--obs-limit", "-o", help="Number of observations to show"
    ),
) -> None:
    """Recover context from last session summaries and observations.

    Returns last N session summaries and last M observations for context recovery
    after compaction or session restart.
    """
    memory_service = ctx.obj
    proj = _get_project_name(project)

    # Use search for deterministic retrieval regardless of observation count
    summaries_raw = memory_service.search("compact/session-summary", limit=summary_limit + 5)
    summaries = [
        obs
        for obs in summaries_raw
        if obs.metadata
        and obs.metadata.get("type") == "session-summary"
        and obs.metadata.get("topic_key") == "compact/session-summary"
    ][:summary_limit]

    # Also fetch artifacts-index
    artifacts_raw = memory_service.search("compact/artifacts-index", limit=1)
    artifacts_index = [
        obs for obs in artifacts_raw
        if obs.metadata and obs.metadata.get("type") == "artifacts-index"
    ]

    # Get recent observations (excluding session summaries)
    all_observations = memory_service.get_recent(limit=observation_limit, offset=0)
    summary_ids = {s.id for s in summaries}
    observations = [obs for obs in all_observations if obs.id not in summary_ids]

    # Display session summaries
    if summaries:
        typer.echo(f"\n=== Last {len(summaries)} Session Summaries ===\n")
        for i, summary in enumerate(summaries, 1):
            from datetime import datetime

            ts = datetime.fromtimestamp(summary.timestamp / 1000)
            meta = summary.metadata or {}
            structured = meta.get("structured", {})

            typer.echo(f"[{i}] {summary.id[:8]}... ({ts.strftime('%Y-%m-%d %H:%M')})")
            if "goal" in structured:
                typer.echo(f"    Goal: {structured['goal']}")
            if "accomplished" in structured:
                typer.echo(f"    Done: {structured['accomplished']}")
            if "next_steps" in structured:
                typer.echo(f"    Next: {', '.join(structured['next_steps'])}")
            if "files" in structured:
                typer.echo(f"    Files: {', '.join(structured['files'][:5])}")
            typer.echo()
    else:
        typer.echo(f"\nNo session summaries found for project: {proj}")

    # Display artifacts index
    if artifacts_index:
        typer.echo("\n=== Artifacts Index ===\n")
        for artifact in artifacts_index:
            meta = artifact.metadata or {}
            structured = meta.get("structured", {})
            if "files" in structured:
                typer.echo("  Files:")
                for f in structured["files"][:10]:
                    typer.echo(f"    - {f}")
            else:
                content = artifact.content[:200]
                typer.echo(f"  {content}")
            typer.echo()

    # Display recent observations
    if observations:
        typer.echo(f"\n=== Last {len(observations)} Observations ===\n")
        for obs in observations[:observation_limit]:
            from datetime import datetime

            ts = datetime.fromtimestamp(obs.timestamp / 1000)
            content = obs.content[:80] + "..." if len(obs.content) > 80 else obs.content
            typer.echo(f"  {obs.id[:8]}... {ts.strftime('%H:%M')} | {content}")
    else:
        typer.echo(f"\nNo observations found for project: {proj}")


@app.command(name="file-ops")
def file_ops(
    ctx: typer.Context,
    read: str | None = typer.Option(
        None, "--read", "-r", help="Files read (comma-separated)"
    ),
    written: str | None = typer.Option(
        None, "--written", "-w", help="Files written (comma-separated)"
    ),
    edited: str | None = typer.Option(
        None, "--edited", "-e", help="Files edited (comma-separated)"
    ),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project name (auto-detected if not provided)"
    ),
) -> None:
    """Save file operation manifest to observations.

    Tracks files that were read, written, or edited during a session for
    context recovery and change tracking.
    """
    if not read and not written and not edited:
        typer.echo("Error: At least one of --read, --written, or --edited must be specified", err=True)
        raise typer.Exit(1)

    memory_service = ctx.obj
    proj = _get_project_name(project)

    # Build file operations manifest
    manifest: dict[str, list[str]] = {}
    if read:
        manifest["read"] = [f.strip() for f in read.split(",") if f.strip()]
    if written:
        manifest["written"] = [f.strip() for f in written.split(",") if f.strip()]
    if edited:
        manifest["edited"] = [f.strip() for f in edited.split(",") if f.strip()]

    # Build metadata
    metadata: dict[str, Any] = {
        "type": "file-ops",
        "project": proj,
        "topic_key": "compact/file-ops",
        "structured": {"manifest": manifest},
    }

    # Generate content
    content_parts = [f"File Operations for {proj}"]
    if "read" in manifest:
        content_parts.append(f"Read: {', '.join(manifest['read'])}")
    if "written" in manifest:
        content_parts.append(f"Written: {', '.join(manifest['written'])}")
    if "edited" in manifest:
        content_parts.append(f"Edited: {', '.join(manifest['edited'])}")

    content = "\n".join(content_parts)

    # Save as observation
    observation = memory_service.save(content=content, metadata=metadata)

    typer.echo(f"File operations saved: {observation.id}")
    typer.echo(f"  Project: {proj}")
    if "read" in manifest:
        typer.echo(f"  Read: {len(manifest['read'])} files")
    if "written" in manifest:
        typer.echo(f"  Written: {len(manifest['written'])} files")
    if "edited" in manifest:
        typer.echo(f"  Edited: {len(manifest['edited'])} files")

    # Flush telemetry
    db_path = _get_db_path_from_context(ctx)
    if db_path:
        telemetry = get_telemetry_service(db_path)
        telemetry.flush()
