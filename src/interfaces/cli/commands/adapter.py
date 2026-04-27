"""Multiplexer adapter CLI commands.

Exposes the auto-detected multiplexer adapter for inspection and operations.
This bridges WS1 (Multiplexer Adapters) to the CLI surface.
"""

from __future__ import annotations

import json
import sys

import typer

app = typer.Typer(help="Terminal multiplexer adapter operations.")


@app.command("detect")
def adapter_detect() -> None:
    """Show which multiplexer adapter is active in this environment."""
    from src.infrastructure.multiplexer.adapter_registry import get_multiplexer_adapter

    adapter = get_multiplexer_adapter()
    if adapter is None:
        print("No multiplexer adapter detected.")
        print("Install tmux, zellij, or run inside iTerm2.")
        raise typer.Exit(code=1)

    print(f"Adapter:  {adapter.name}")
    print("Detected: True")


@app.command("spawn")
def adapter_spawn(
    command: str = typer.Argument(..., help="Command to run in new pane"),
    name: str | None = typer.Option(None, "--name", "-n", help="Pane name"),
    workdir: str | None = typer.Option(None, "--workdir", "-w", help="Working directory"),
) -> None:
    """Spawn a command in a new multiplexer pane using the auto-detected adapter."""
    from src.domain.ports.multiplexer_adapter import SpawnOptions
    from src.infrastructure.multiplexer.adapter_registry import get_multiplexer_adapter

    adapter = get_multiplexer_adapter()
    if adapter is None:
        print("No multiplexer adapter detected.", file=sys.stderr)
        raise typer.Exit(code=1)

    options = SpawnOptions(command=command, name=name, workdir=workdir)
    pane = adapter.spawn(options)

    # Output pane info as JSON for machine consumption
    print(json.dumps({"pane_id": pane.pane_id, "is_alive": pane.is_alive, "title": pane.title}))


@app.command("kill")
def adapter_kill(
    pane_id: str = typer.Argument(..., help="Pane ID to kill"),
) -> None:
    """Kill a multiplexer pane by its ID."""
    from src.infrastructure.multiplexer.adapter_registry import get_multiplexer_adapter

    adapter = get_multiplexer_adapter()
    if adapter is None:
        print("No multiplexer adapter detected.", file=sys.stderr)
        raise typer.Exit(code=1)

    adapter.kill(pane_id)
    print(f"Killed pane: {pane_id}")


@app.command("alive")
def adapter_alive(
    pane_id: str = typer.Argument(..., help="Pane ID to check"),
) -> None:
    """Check if a multiplexer pane is still alive."""
    from src.infrastructure.multiplexer.adapter_registry import get_multiplexer_adapter

    adapter = get_multiplexer_adapter()
    if adapter is None:
        print("No multiplexer adapter detected.", file=sys.stderr)
        raise typer.Exit(code=1)

    alive = adapter.is_alive(pane_id)
    print(f"Alive: {alive}")


@app.command("title")
def adapter_title(
    pane_id: str = typer.Argument(..., help="Pane ID"),
    title: str = typer.Argument(..., help="New title"),
) -> None:
    """Set the title of a multiplexer pane."""
    from src.infrastructure.multiplexer.adapter_registry import get_multiplexer_adapter

    adapter = get_multiplexer_adapter()
    if adapter is None:
        print("No multiplexer adapter detected.", file=sys.stderr)
        raise typer.Exit(code=1)

    adapter.set_title(pane_id, title)
    print(f"Title set: {title}")
