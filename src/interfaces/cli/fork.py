"""CLI para bifurcar terminals y operaciones de doctor.

Este módulo proporciona una CLI para bifurcar sesiones de terminal
y ejecutar comandos de diagnóstico/del doctor.
"""

from __future__ import annotations

import json as json_mod
import subprocess
import sys
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import typer

from src.application.services.agent.agent_manager import (
    get_agent_manager,
)
from src.domain.entities.terminal import TerminalResult

# Tipo para la función de bifurcación
ForkTerminalFn = Callable[[str], TerminalResult]

# Doctor app
doctor_app = typer.Typer(name="doctor", help="Diagnóstico y reparación del sistema")

from src.interfaces.cli.commands.adapter import app as adapter_app  # noqa: E402
from src.interfaces.cli.commands.message import app as message_app  # noqa: E402
from src.interfaces.cli.commands.poll import app as poll_app  # noqa: E402
from src.interfaces.cli.commands.task import app as task_app  # noqa: E402
from src.interfaces.cli.commands.template import app as template_app  # noqa: E402

# Root app that combines fork CLI and doctor commands
root_app = typer.Typer(name="fork", help="Fork terminal operations and doctor diagnostics")
root_app.add_typer(doctor_app)
root_app.add_typer(message_app, name="message")
root_app.add_typer(poll_app, name="poll")
root_app.add_typer(task_app, name="task")
root_app.add_typer(adapter_app, name="adapter")
root_app.add_typer(template_app, name="template")


def create_fork_cli(
    fork_terminal: ForkTerminalFn,
) -> Callable[[], int]:
    """Factory function para crear la CLI con dependencias inyectadas.

    Args:
        fork_terminal: Función que ejecuta el fork de terminal.

    Returns:
        Función main lista para ejecutar.
    """

    def main() -> int:
        """Punto de entrada principal de la CLI.

        Returns:
            Código de salida (0 para éxito, 1 para error).
        """
        if len(sys.argv) < 2:
            print("Uso: fork <comando>")
            return 1

        command = " ".join(sys.argv[1:])

        try:
            result = fork_terminal(command)
            print(result.output)
            return result.exit_code
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    return main


@root_app.command("run")
def fork_run(
    command: str = typer.Argument(..., help="Command to execute in forked terminal"),
) -> None:
    """Run a command in a forked terminal."""
    from src.application.services.terminal.platform_detector import PlatformDetectorImpl
    from src.application.services.terminal.terminal_spawner import TerminalSpawnerImpl
    from src.application.use_cases.fork_terminal import fork_terminal_use_case

    platform_detector = PlatformDetectorImpl()
    terminal_spawner = TerminalSpawnerImpl()
    fork_terminal = fork_terminal_use_case(platform_detector, terminal_spawner)

    result = fork_terminal(command)
    print(result.output)
    raise typer.Exit(code=result.exit_code)


@doctor_app.command("reconcile")
def doctor_reconcile() -> None:
    """Reconcile tmux sessions with registered agents.

    Shows orphaned sessions (in tmux but not registered) and
    missing sessions (registered but not in tmux).
    """
    manager = get_agent_manager()
    result = manager.reconcile_sessions()

    print("=== Reconcile Results ===")
    print(f"Status: {result.status}")
    print(f"Registered agents: {len(result.registered_agents)}")
    for session in result.registered_agents:
        print(f"  - {session}")
    print(f"Runtime sessions: {len(result.runtime_sessions)}")
    for session in result.runtime_sessions:
        print(f"  - {session}")
    print(f"Orphaned sessions: {len(result.orphaned_sessions)}")
    for session in result.orphaned_sessions:
        print(f"  - {session} (NOT registered)")
    print(f"Missing sessions: {len(result.missing_sessions)}")
    for session in result.missing_sessions:
        print(f"  - {session} (NOT in tmux)")


@doctor_app.command("cleanup-orphans")
def doctor_cleanup_orphans(
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Simulate cleanup without actually cleaning"
    ),
    min_age: int = typer.Option(0, "--min-age", help="Only clean sessions older than N seconds"),
    force: bool = typer.Option(False, "--force", help="Require confirmation before cleaning"),
) -> None:
    """Clean up orphaned tmux sessions.

    By default runs in dry-run mode. Use --no-dry-run to actually clean.
    Use --force to skip confirmation prompt.
    """
    if not dry_run and not force:
        typer.confirm("This will DELETE orphaned tmux sessions. Continue?", abort=True)

    manager = get_agent_manager()
    result = manager.cleanup_orphans(dry_run=dry_run, min_age_seconds=min_age)

    print("=== Cleanup Results ===")
    print(f"Dry run: {result.dry_run}")
    print(f"Cleaned sessions: {len(result.cleaned_sessions)}")
    for session in result.cleaned_sessions:
        print(f"  - {session}")
    print(f"Failed sessions: {len(result.failed_sessions)}")
    for session in result.failed_sessions:
        print(f"  - {session}")


@doctor_app.command("status")
def doctor_status(
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """Show health status including orphan session count."""
    manager = get_agent_manager()
    status = manager.get_health_status()

    if json_output:
        import json

        # Prepare JSON output with fields expected by health gate scripts
        output = {
            "tmux_installed": True,
            "status": status.get("reconcile_status", "unknown"),
            "orphan_sessions": status.get("orphan_sessions_count", 0),
            "registered_count": status.get("registered_count", 0),
            "runtime_sessions_count": status.get("runtime_sessions_count", 0),
        }
        # Add Trifecta graph info
        trifecta_info = _get_trifecta_status()
        if trifecta_info:
            output["trifecta"] = trifecta_info
        print(json.dumps(output))
        return

    print("=== Health Status ===")
    print(f"Reconcile status: {status['reconcile_status']}")
    print(f"Registered agents: {status['registered_count']}")
    print(f"Runtime sessions: {status['runtime_sessions_count']}")
    print(f"Orphan sessions: {status['orphan_sessions_count']}")
    if status["orphan_sessions"]:
        print("Orphan session names:")
        for session in cast(Iterable[str], status["orphan_sessions"]):
            print(f"  - {session}")

    # Trifecta graph health
    _print_trifecta_status()


def _get_trifecta_status() -> dict | None:
    """Get Trifecta graph status as dict (for JSON output)."""
    try:
        repo_path = Path.cwd()
        result = subprocess.run(
            ["trifecta", "graph", "status", "-s", str(repo_path), "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return json_mod.loads(result.stdout)  # type: ignore[no-any-return]
    except (FileNotFoundError, subprocess.TimeoutExpired, json_mod.JSONDecodeError):
        pass
    return None


def _print_trifecta_status() -> None:
    """Print Trifecta graph health status line."""
    info = _get_trifecta_status()
    if not info:
        print("Trifecta Graph:          CLI not found")
        return

    node_count = info.get("node_count", 0)
    edge_count = info.get("edge_count", 0)
    last_indexed = info.get("last_indexed_at", "never")
    graph_exists = info.get("exists", False)

    if not graph_exists or node_count == 0:
        print("Trifecta Graph:          not initialized")
        return

    staleness = ""
    if last_indexed and last_indexed != "never":
        try:
            indexed_time = datetime.fromisoformat(last_indexed.replace("Z", "+00:00"))
            age_hours = (datetime.now(UTC) - indexed_time).total_seconds() / 3600
            if age_hours < 1:
                staleness = f"{int(age_hours * 60)}m ago (fresh)"
            elif age_hours < 24:
                staleness = f"{int(age_hours)}h ago (fresh)"
            else:
                staleness = f"{int(age_hours)}h ago (STALE)"
        except Exception:
            staleness = last_indexed

    print(f"Trifecta Graph:          {node_count} nodes, {edge_count} edges | {staleness}")


def run_cli() -> int:
    """Ejecuta la CLI con las implementaciones por defecto.

    Returns:
        Código de salida.
    """
    # Run the root app with sys.argv
    root_app()
    return 0


if __name__ == "__main__":
    root_app()
