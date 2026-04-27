"""Sync command for CLI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from src.application.services.sync.sync_service import SyncService
from src.infrastructure.persistence.container import (
    create_container,
    get_default_data_dir,
    get_default_db_path,
    get_sync_service,
)
from src.infrastructure.sync.git_sync import GitSyncBackend

app = typer.Typer(help="Sync operations: export, import, status")


@app.command(name="export")
def export_cmd(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", "-p", help="Optional project filter"),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Output directory for export"
    ),
    chunk_size: int = typer.Option(100, "--chunk-size", "-c", help="Observations per chunk"),
) -> None:
    """Export observations to gzipped JSONL chunks."""
    if output_dir is not None:
        container = create_container(_get_db_path(ctx), export_dir=output_dir)
        sync_service = container.sync_service()
    else:
        sync_service = get_sync_service()
    paths = sync_service.export_observations(project=project, chunk_size=chunk_size)
    if paths:
        for path in paths:
            typer.echo(f"Created: {path}")
        typer.echo(f"Exported to {len(paths)} chunk(s)")
    else:
        typer.echo("No observations to export")


@app.command(name="import")
def import_cmd(
    ctx: typer.Context,
    chunk_paths: list[Path] = typer.Argument(..., help="Chunk file(s) to import"),
    source: str = typer.Option("import", "--source", "-s", help="Source identifier"),
) -> None:
    """Import observations from JSONL chunk files."""
    sync_service = get_sync_service(_get_db_path(ctx))

    # Look for manifest file alongside chunks
    manifest_path = None
    if chunk_paths:
        chunk_dir = chunk_paths[0].parent
        manifest_files = sorted(chunk_dir.glob("manifest_*.json"))
        if manifest_files:
            manifest_path = manifest_files[0]
            typer.echo(f"Using manifest: {manifest_path.name}")
        else:
            typer.echo("Warning: No manifest file found. Checksum validation skipped.", err=True)

    imported = sync_service.import_observations(
        chunk_paths=chunk_paths, source=source, manifest_path=manifest_path
    )
    typer.echo(f"Imported {imported} observation(s)")


@app.command(name="status")
def status_cmd(ctx: typer.Context) -> None:
    """Show sync status."""
    sync_service = get_sync_service(_get_db_path(ctx))
    sync_status = sync_service.get_status()
    typer.echo("Sync Status:")
    typer.echo(f"  Total observations: {sync_status['total_observations']}")
    typer.echo(f"  Mutation count: {sync_status['mutation_count']}")
    typer.echo(f"  Latest sequence: {sync_status['latest_seq']}")
    typer.echo(f"  Last export seq: {sync_status['last_export_seq']}")
    if sync_status["last_export_at"]:
        last_export = datetime.fromtimestamp(sync_status["last_export_at"] / 1000).isoformat()
        typer.echo(f"  Last export: {last_export}")
    else:
        typer.echo("  Last export: never")
    if sync_status["last_import_at"]:
        last_import = datetime.fromtimestamp(sync_status["last_import_at"] / 1000).isoformat()
        typer.echo(f"  Last import: {last_import}")
    else:
        typer.echo("  Last import: never")


def _get_db_path(ctx: typer.Context) -> Path:
    """Get database path from CLI context."""
    current: Any = ctx
    while current:
        if hasattr(current, "params") and "db_path" in current.params:
            db_path = current.params["db_path"]
            return Path(db_path).expanduser()
        if hasattr(current, "parent"):
            current = current.parent
        else:
            break
    return get_default_db_path()


def _make_sync_service(ctx: typer.Context) -> SyncService:
    """Build a SyncService from CLI context."""
    return get_sync_service(_get_db_path(ctx))  # type: ignore[no-any-return]


@app.command(name="push")
def push_cmd(
    ctx: typer.Context,
    remote: str | None = typer.Option(None, "--remote", "-r", help="Git remote URL"),
    chunk_size: int = typer.Option(100, "--chunk-size", "-c", help="Mutations per chunk"),
) -> None:
    """Incremental export + git push."""
    sync_service = _make_sync_service(ctx)
    paths = sync_service.export_incremental(chunk_size=chunk_size, commit_watermark=False)
    if not paths:
        typer.echo("No new mutations to push")
        return

    typer.echo(f"Exported {len(paths)} mutation chunk(s)")

    git = GitSyncBackend(sync_dir=get_default_data_dir() / "sync", remote_url=remote)
    git.init_repo()
    ok = git.push(paths)
    if ok:
        sync_service.commit_export_watermark()
        typer.echo("Push successful")
    else:
        typer.echo("Push failed (see logs)", err=True)
        raise typer.Exit(code=1)


@app.command(name="pull")
def pull_cmd(
    ctx: typer.Context,
    remote: str | None = typer.Option(None, "--remote", "-r", help="Git remote URL"),
) -> None:
    """Git pull + import mutations."""
    git = GitSyncBackend(sync_dir=get_default_data_dir() / "sync", remote_url=remote)
    git.init_repo()

    new_chunks = git.pull()
    if not new_chunks:
        typer.echo("No new chunks to import")
        return

    typer.echo(f"Pulled {len(new_chunks)} chunk(s)")
    sync_service = _make_sync_service(ctx)
    counts = sync_service.import_mutations(new_chunks, source="pull")
    typer.echo(
        f"Applied: {counts['inserted']} inserted, "
        f"{counts['updated']} updated, "
        f"{counts['deleted']} deleted"
    )


@app.command(name="log")
def log_cmd(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-n", help="Max entries"),
) -> None:
    """Show mutation journal."""
    sync_service = _make_sync_service(ctx)
    mutations = sync_service.get_mutations_since(0)[:limit]

    if not mutations:
        typer.echo("No mutations recorded")
        return

    typer.echo(f"{'SEQ':>6}  {'OP':<8}  {'ENTITY':<14}  {'SOURCE':<10}  {'TIME'}")
    typer.echo("-" * 70)
    for m in mutations:
        ts = (
            datetime.fromtimestamp(m.created_at / 1000).strftime("%Y-%m-%d %H:%M")
            if m.created_at
            else "-"
        )
        typer.echo(f"{m.seq:>6}  {m.op:<8}  {m.entity_key[:14]:<14}  {m.source:<10}  {ts}")
