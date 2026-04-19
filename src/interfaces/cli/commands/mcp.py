"""MCP server command — start MCP stdio server."""

from __future__ import annotations

import os
import sys

import typer

app = typer.Typer(
    name="mcp",
    help="MCP server for agent integrations.",
    no_args_is_help=True,
)


@app.command(name="serve")
def serve(
    db_path: str = typer.Option(
        None,
        "--db",
        "-d",
        envvar="FORK_MEMORY_DB",
        help="Path to memory database (default: XDG-compliant, env: FORK_MEMORY_DB)",
    ),
) -> None:
    """Start the MCP stdio server.

    The server communicates via JSON-RPC on stdin/stdout.
    All logging goes to stderr.
    """
    if db_path:
        os.environ["FORK_MEMORY_DB"] = db_path

    # Initialize the MCP service with the configured DB path
    from src.interfaces.mcp.tools import init_service

    init_service(db_path)

    # Configure logging to stderr before importing server
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,
    )

    from src.interfaces.mcp.server import run_server

    run_server()
