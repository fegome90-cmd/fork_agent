"""Import command for CLI."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Import observations from external formats")


@app.command("obsidian")
def obsidian(
    ctx: typer.Context,
    input_dir: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Input directory (vault/export root)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    project: str | None = typer.Option(
        None, "--project", help="Override project for all imported observations"
    ),
    skip_duplicates: bool = typer.Option(
        False, "--skip-duplicates", help="Skip files whose id already exists in DB"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show per-file import details"),
) -> None:
    """Import Obsidian-compatible markdown files as observations."""
    from src.application.services.import_.obsidian_import_service import ObsidianImportService

    service = ctx.obj

    # Gather existing IDs from DB for duplicate detection
    existing_ids: set[str] = set()
    if skip_duplicates:
        try:
            all_obs = service.get_recent(limit=10000)
            existing_ids = {obs.id for obs in all_obs}
        except Exception as exc:
            typer.echo(f"Warning: could not fetch existing IDs: {exc}", err=True)

    importer = ObsidianImportService()

    if dry_run:
        typer.echo(f"Dry run: scanning {input_dir} for .md files...")
        # We need a fake save for dry-run count
        result = importer.import_from_dir(
            input_dir=input_dir,
            memory_save_fn=lambda **_kw: "dry-run-id",
            existing_ids=existing_ids,
            dry_run=True,
            project_override=project,
            skip_duplicates=skip_duplicates,
        )
        typer.echo(f"Would import {result.total_files} files ({result.skipped} duplicates skipped)")
        return

    def save_wrapper(**kwargs: object) -> str:
        """Bridge between import service kwargs and MemoryService.save()."""
        obs = service.save(**kwargs)  # noqa: ANN204
        return str(obs.id)

    result = importer.import_from_dir(
        input_dir=input_dir,
        memory_save_fn=save_wrapper,
        existing_ids=existing_ids,
        dry_run=False,
        project_override=project,
        skip_duplicates=skip_duplicates,
    )

    # Output summary
    typer.echo(
        f"Imported {result.imported}/{result.total_files} files "
        f"({result.skipped} skipped, {len(result.errors)} errors)"
    )

    if verbose and result.imported_ids:
        for oid in result.imported_ids:
            typer.echo(f"  imported: {oid}")

    if verbose and result.errors:
        for err in result.errors:
            typer.echo(f"  error: {err}", err=True)
