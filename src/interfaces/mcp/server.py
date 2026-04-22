"""MCP server for tmux_fork memory operations (stdio, SSE, streamable-http)."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from starlette.applications import Starlette

from src.interfaces.mcp import tools  # noqa: F401


def _configure_logging() -> None:
    """Configure logging to stderr only — stdout is reserved for JSON-RPC."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,
    )


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server instance.

    Returns:
        Configured FastMCP instance with all tools registered.
    """
    _configure_logging()

    from mcp.server.fastmcp import FastMCP

    mcp_server = FastMCP("memory-server")
    tools.register_tools(mcp_server)
    return mcp_server


def _wrap_with_auth(app: Starlette) -> Starlette:
    """Wrap a Starlette app with Bearer auth middleware for SSE/HTTP transports.

    Only adds middleware when ``FORK_MCP_TOKEN`` is set.  When the env var
    is absent the verifier accepts every request (local-dev friendly).

    Returns the *app* unchanged when no token is configured, to avoid
    adding unnecessary latency.
    """
    import os

    if not os.environ.get("FORK_MCP_TOKEN"):
        return app

    from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend
    from starlette.applications import Starlette
    from starlette.middleware.authentication import AuthenticationMiddleware

    from src.interfaces.mcp.auth import ApiKeyTokenVerifier

    verifier = ApiKeyTokenVerifier()
    backend = BearerAuthBackend(verifier)

    if isinstance(app, Starlette):
        app.add_middleware(AuthenticationMiddleware, backend=backend)
    return app


def run_server(
    transport: str = "stdio",
    mount_path: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    """Entry point for the MCP server.

    Args:
        transport: Transport protocol ("stdio", "sse", or "streamable-http").
        mount_path: Mount path for HTTP-based transports.
        host: Host address for SSE/streamable-http transports.
        port: Port for SSE/streamable-http transports.
    """
    _configure_logging()
    mcp_server = create_mcp_server()
    if transport == "stdio":
        # stdio is always local/trusted — no auth.
        mcp_server.run(transport="stdio")
    elif transport in ("sse", "streamable-http"):
        import uvicorn

        app = (
            mcp_server.sse_app(mount_path=mount_path)
            if transport == "sse"
            else mcp_server.streamable_http_app(mount_path=mount_path)  # type: ignore[call-arg]
        )
        app = _wrap_with_auth(app)
        uvicorn.run(app, host=host, port=port)
    else:
        print(f"Error: unsupported transport '{transport}'", file=sys.stderr)
        sys.exit(1)


def run_server_cli() -> None:
    """CLI entry point for the MCP server with --db argument support.

    Parses command-line arguments, initializes the service with a custom
    DB path if provided, then starts the stdio MCP server.

    Usage:
        memory-mcp
        memory-mcp --db /path/to/custom.db
        memory-mcp -d /path/to/custom.db
    """
    from src.infrastructure.persistence.container import get_default_db_path

    parser = argparse.ArgumentParser(
        prog="memory-mcp",
        description="MCP server for tmux_fork memory operations.",
    )
    parser.add_argument(
        "--db",
        "-d",
        default=None,
        help=("Path to memory database (default: XDG-compliant, env: FORK_MEMORY_DB)"),
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--mount-path",
        default=None,
        help="Mount path for HTTP-based transports",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for HTTP-based transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP-based transports (default: 8080)",
    )

    args = parser.parse_args()

    if args.port < 1 or args.port > 65535:
        print(f"Error: port must be between 1 and 65535, got {args.port}", file=sys.stderr)
        sys.exit(1)

    db_path = args.db or os.environ.get("FORK_MEMORY_DB") or str(get_default_db_path())

    os.environ["FORK_MEMORY_DB"] = db_path
    from src.interfaces.mcp.tools import init_service

    init_service(db_path)

    run_server(
        transport=args.transport,
        mount_path=args.mount_path,
        host=args.host,
        port=args.port,
    )
