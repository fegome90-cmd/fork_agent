"""Entry point for running MCP server as a module: python -m src.interfaces.mcp.server."""

from __future__ import annotations

from src.interfaces.mcp.server import run_server_cli

if __name__ == "__main__":
    run_server_cli()
