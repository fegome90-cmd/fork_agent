"""Export command for CLI."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Export observations to external formats")


@app.command()
def obsidian(
    ctx: typer.Context,
    output: Path = typer.Option("./export", "--output", "-o", help="Output directory"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    type_: str | None = typer.Option(None, "--type", "-t", help="Filter by type"),
    topic_key: str | None = typer.Option(
        None, "--topic-key", "-k", help="Filter by topic_key prefix"
    ),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Max observations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
) -> None:
    """Export observations as Obsidian-compatible markdown files."""
    from src.application.services.export.obsidian_export_service import ObsidianExportService

    service = ctx.obj
    observations = service.get_recent(limit=limit or 1000)

    if project:
        observations = [o for o in observations if o.project == project]
    if type_:
        observations = [o for o in observations if o.type == type_]
    if topic_key:
        observations = [
            o for o in observations if o.topic_key and o.topic_key.startswith(topic_key)
        ]

    if dry_run:
        typer.echo(f"Would export {len(observations)} observations to {output}")
        for o in observations[:10]:
            typer.echo(f"  {o.topic_key or o.id[:8]} ({o.type})")
        if len(observations) > 10:
            typer.echo(f"  ... and {len(observations) - 10} more")
        return

    exporter = ObsidianExportService()
    created = exporter.export(observations, output)
    typer.echo(f"Exported {len(created)} observations to {output}")
