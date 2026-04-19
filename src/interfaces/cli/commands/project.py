"""Project management commands for CLI."""

from __future__ import annotations

from typing import Any

import typer

app = typer.Typer(help="Project management commands")


@app.command("merge")
def merge(
    ctx: typer.Context,
    from_projects: str = typer.Option(..., "--from", "-f", help="Comma-separated source project(s) to merge FROM"),
    to_project: str = typer.Option(..., "--to", "-t", help="Target project to merge INTO"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Merge observations from one or more projects into a target project."""
    memory_service = ctx.obj

    if dry_run:
        typer.echo(f"DRY RUN - Preview of merge '{from_projects}' -> '{to_project}':")
        source_list = [s.strip() for s in from_projects.split(",") if s.strip()]
        typer.echo(f"  Source projects: {source_list}")
        typer.echo(f"  Target project: {to_project}")
        typer.echo("  Use --force to apply.")
        return

    if not force:
        typer.echo(f"Will merge '{from_projects}' -> '{to_project}'")
        confirm = typer.confirm("Proceed?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Abort()

    result: dict[str, Any] = memory_service.merge_projects(from_projects, to_project)
    typer.echo(f"Merged {result.get('observations_updated', 0)} observations into '{to_project}'")
    if result.get("sessions_updated"):
        typer.echo(f"Updated {result['sessions_updated']} sessions")
    if result.get("sources_merged"):
        typer.echo(f"Source projects: {result['sources_merged']}")
