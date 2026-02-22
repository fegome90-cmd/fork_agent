"""Memory CLI - Main entry point."""

from __future__ import annotations

from pathlib import Path

import typer

from src.interfaces.cli.commands import delete, get, list, save, search
from src.interfaces.cli.dependencies import get_memory_service

app = typer.Typer(
    name="memory",
    help="Manage agent memory observations",
)

app.command(name="save")(save.save)
app.command(name="search")(search.search)
app.command(name="list")(list.list_observations)
app.command(name="get")(get.get)
app.command(name="delete")(delete.delete)


@app.callback()
def main(
    ctx: typer.Context,
    db_path: str = typer.Option(
        "data/memory.db",
        "--db",
        "-d",
        help="Path to memory database",
    ),
) -> None:
    ctx.obj = get_memory_service(Path(db_path))


if __name__ == "__main__":
    app()
