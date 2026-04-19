"""TUI CLI entry point."""

from __future__ import annotations

import typer

app = typer.Typer(help="Launch Memory TUI")


@app.command("tui")
def launch(
    ctx: typer.Context,
    db: str | None = typer.Option(None, "--db", help="Database path (default: XDG data dir)"),
) -> None:
    """Launch the Memory TUI browser."""
    from src.interfaces.tui.app import TUIApp

    db_path = db  # CLI flag takes priority
    if db_path is None and hasattr(ctx.obj, "db_path"):
        db_path = ctx.obj.db_path
    tui_app = TUIApp(db_path=db_path)
    tui_app.run()
