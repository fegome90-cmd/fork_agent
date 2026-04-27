"""MCP server command — start MCP stdio server, background server management."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time

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


@app.command()
def start(
    port: int = typer.Option(0, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
) -> None:
    """Start MCP server in background (streamable-http).

    Auto-assigns an available port. Server info written to
    ~/.local/share/fork/.mcp-server.json. Use FORK_HYBRID=1 to route
    CLI commands through this server.
    """
    from pathlib import Path

    data_dir = Path(os.environ.get("FORK_DATA_DIR", os.path.expanduser("~/.local/share/fork")))
    data_dir.mkdir(parents=True, exist_ok=True)
    port_file = data_dir / ".mcp-server.json"

    # B3: Guard against double-start — check if existing server is alive
    if port_file.exists():
        try:
            info = json.loads(port_file.read_text())
            old_pid = info["pid"]
            os.kill(old_pid, 0)  # Raises OSError if dead
            typer.echo(f"MCP server already running (PID={old_pid}, port={info['port']})", err=True)
            raise SystemExit(1)
        except (json.JSONDecodeError, KeyError, OSError):
            # Stale or corrupt port file — clean up
            port_file.unlink(missing_ok=True)

    if port == 0:
        s = socket.socket()
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()

    cmd = [
        sys.executable,
        "-m",
        "src.interfaces.mcp.server",
        "--transport",
        "streamable-http",
        "--port",
        str(port),
        "--host",
        host,
    ]
    # Inherit FORK_MEMORY_DB if set, otherwise pass default DB path
    env = os.environ.copy()
    from src.infrastructure.persistence.container import get_default_db_path

    if "FORK_MEMORY_DB" not in env:
        env["FORK_MEMORY_DB"] = str(get_default_db_path())
    proc = subprocess.Popen(
        cmd,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    db_path = env.get("FORK_MEMORY_DB", str(get_default_db_path()))

    # A1: Atomic write — temp file then rename (POSIX guarantees atomicity)
    port_data = json.dumps(
        {
            "pid": proc.pid,
            "port": port,
            "host": host,
            "transport": "streamable-http",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "db_path": db_path,
        }
    )
    tmp_file = port_file.with_suffix(".tmp")
    tmp_file.write_text(port_data)
    os.replace(str(tmp_file), str(port_file))
    typer.echo(f"MCP server started (PID={proc.pid}, port={port})")


@app.command()
def stop() -> None:
    """Stop background MCP server.

    Sends SIGTERM, escalates to SIGKILL after 2s if still alive.
    Removes the port file on cleanup.
    """
    from src.interfaces.cli.hybrid import _get_port_file, discover_server

    info = discover_server()
    if info is None:
        typer.echo("No MCP server running")
        raise typer.Exit(0)
    pid = info["pid"]
    os.kill(pid, 15)  # SIGTERM
    time.sleep(0.5)
    try:
        os.kill(pid, 0)
        os.kill(pid, 9)  # SIGKILL if still alive
    except ProcessLookupError:
        pass
    _get_port_file().unlink(missing_ok=True)
    typer.echo(f"MCP server stopped (PID={pid})")


@app.command()
def status() -> None:
    """Check MCP server status.

    Verifies PID is alive and /health endpoint responds.
    Exits 0 if healthy, 1 if not responding.
    """
    import httpx

    from src.interfaces.cli.hybrid import discover_server

    info = discover_server()
    if info is None:
        typer.echo("No MCP server running (no port file or stale PID)")
        raise typer.Exit(1)
    try:
        httpx.get(f"http://{info['host']}:{info['port']}/health", timeout=1.5)
        typer.echo(f"MCP server alive (PID={info['pid']}, port={info['port']})")
    except (httpx.ConnectError, httpx.TimeoutException):
        typer.echo(f"MCP server NOT responding (PID={info['pid']}, port={info['port']})")
        raise typer.Exit(1)  # noqa: B904
