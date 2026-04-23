"""CLI commands for autonomous agent polling."""

from __future__ import annotations

import signal
import time
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.table import Table

from src.application.exceptions import RepositoryError
from src.domain.entities.poll_run import PollRunStatus

if TYPE_CHECKING:
    from src.application.services.agent_polling_service import AgentPollingService

app = typer.Typer(help="Autonomous agent polling operations.")
console = Console()


def _get_service() -> AgentPollingService:
    """Build an AgentPollingService via the DI container."""
    from src.infrastructure.persistence.container import get_agent_polling_service

    return get_agent_polling_service()


@app.command("start")
def start_polling(
    interval: Annotated[
        int, typer.Option("--interval", "-i", help="Poll interval in seconds")
    ] = 10,
    max_concurrent: Annotated[
        int, typer.Option("--max-concurrent", "-m", help="Max concurrent agents")
    ] = 4,
) -> None:
    """Start the autonomous polling loop. Press Ctrl+C to stop."""
    from src.infrastructure.persistence.container import get_agent_polling_service

    service = get_agent_polling_service()
    # Override defaults if specified
    service._max_concurrent = max_concurrent  # noqa: SLF001
    service._poll_interval = interval  # noqa: SLF001

    console.print(
        f"[green]Polling started[/green] (interval={interval}s, max_concurrent={max_concurrent}). Ctrl+C to stop."
    )

    running = True
    total_spawned = 0
    total_completed = 0
    total_failed = 0

    def handle_sigint(_sig: int, _frame: object) -> None:
        nonlocal running
        running = False
        console.print("\n[yellow]Shutting down...[/yellow]")

    signal.signal(signal.SIGINT, handle_sigint)

    while running:
        try:
            # Poll for new tasks
            new_runs = service.poll_once()
            total_spawned += len(new_runs)
            for run in new_runs:
                console.print(
                    f"  [cyan]Spawned[/cyan] run {run.id[:8]}... for task {run.task_id[:8]}..."
                )

            # Check active runs
            updated = service.check_runs()
            for run in updated:
                if run.status == PollRunStatus.COMPLETED:
                    total_completed += 1
                    console.print(
                        f"  [green]Completed[/green] run {run.id[:8]}... (task {run.task_id[:8]}...)"
                    )
                elif run.status == PollRunStatus.FAILED:
                    total_failed += 1
                    error = run.error_message or "unknown"
                    console.print(f"  [red]Failed[/red] run {run.id[:8]}... ({error[:50]})")

            # Show status line
            active = service.get_active_runs()
            if active or new_runs:
                console.print(
                    f"  [dim]Active: {len(active)} | Total: {total_spawned} spawned, {total_completed} done, {total_failed} failed[/dim]"
                )

        except (ValueError, RepositoryError) as e:
            console.print(f"  [red]Error: {e}[/red]")
        except Exception as e:
            console.print(f"  [red]Unexpected: {e}[/red]")

        # Sleep in small increments for responsive Ctrl+C
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    # Graceful shutdown summary
    console.print("\n[bold]Polling stopped.[/bold]")
    console.print(f"  Spawned:  {total_spawned}")
    console.print(f"  Completed: {total_completed}")
    console.print(f"  Failed:  {total_failed}")


@app.command("status")
def show_status() -> None:
    """Show active and recent poll runs."""
    service = _get_service()
    try:
        summary = service.get_status_summary()
        active = service.get_active_runs()
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e

    console.print("\n[bold]Poll Run Summary[/bold]")
    for status_name, count in summary.items():
        style = (
            "green"
            if status_name == "COMPLETED"
            else "red"
            if status_name == "FAILED"
            else "yellow"
            if status_name == "RUNNING"
            else "dim"
        )
        console.print(f"  [{style}]{status_name}[/{style}]: {count}")

    if active:
        table = Table(title="Active Runs")
        table.add_column("Run ID", style="cyan", max_width=8)
        table.add_column("Task ID", style="white", max_width=8)
        table.add_column("Agent", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Started", style="dim")
        for run in active:
            started = (
                datetime.fromtimestamp((run.started_at or 0) / 1000).strftime("%H:%M:%S")
                if run.started_at
                else "-"
            )
            table.add_row(run.id[:8], run.task_id[:8], run.agent_name, run.status.value, started)
        console.print(table)


@app.command("cancel")
def cancel_run(
    run_id: Annotated[str, typer.Argument(help="Run ID to cancel")],
) -> None:
    """Cancel an active poll run."""
    service = _get_service()
    try:
        run = service.cancel_run(run_id)
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected: {e}[/red]")
        raise typer.Exit(1) from None

    console.print(f"[yellow]Run {run.id[:8]}... cancelled.[/yellow]")


@app.command("list-tasks")
def list_approved_tasks() -> None:
    """Show APPROVED tasks awaiting execution."""
    from src.infrastructure.persistence.container import get_task_board_service

    service = get_task_board_service()
    try:
        from src.domain.entities.orchestration_task import OrchestrationTaskStatus

        tasks = service.list(status=OrchestrationTaskStatus.APPROVED)
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None

    if not tasks:
        console.print("No approved tasks found.")
        return

    table = Table(title="Approved Tasks")
    table.add_column("ID", style="cyan", max_width=8)
    table.add_column("Subject", style="white")
    table.add_column("Owner", style="magenta")
    table.add_column("Created", style="dim")

    for task in tasks:
        created = datetime.fromtimestamp(task.created_at / 1000).strftime("%Y-%m-%d %H:%M")
        table.add_row(task.id[:8], task.subject, task.owner or "-", created)

    console.print(table)
