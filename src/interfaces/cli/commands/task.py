"""CLI commands for orchestration task management."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from src.application.exceptions import RepositoryError
from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.orchestration_task import OrchestrationTaskStatus

app = typer.Typer(help="Manage orchestration tasks.")
console = Console()


def _get_service() -> TaskBoardService:
    """Build a TaskBoardService via the infrastructure container."""
    from src.infrastructure.persistence.container import get_task_board_service

    return get_task_board_service()


def _default_requester() -> str:
    """Return the current OS user as a default requester identity."""
    return os.environ.get("USER", "unknown")


def _format_timestamp(ms: int) -> str:
    """Format a millisecond epoch timestamp into a readable string."""
    if ms <= 0:
        return "-"
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")


@app.command("create")
def create_task(
    subject: Annotated[str, typer.Option(..., help="Task subject/title")],
    description: Annotated[str | None, typer.Option(help="Task description")] = None,
    owner: Annotated[str | None, typer.Option(help="Task owner")] = None,
) -> None:
    """Create a new orchestration task."""
    service = _get_service()
    try:
        task = service.create(subject=subject, description=description, owner=owner)
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[green]Task created successfully.[/green]")
    console.print(f"  ID:          {task.id}")
    console.print(f"  Subject:     {task.subject}")
    if task.description:
        console.print(f"  Description: {task.description}")
    if task.owner:
        console.print(f"  Owner:       {task.owner}")
    console.print(f"  Status:      {task.status.value}")
    console.print(f"  Created:     {_format_timestamp(task.created_at)}")


@app.command("list")
def list_tasks(
    status: Annotated[str | None, typer.Option(help="Filter by status")] = None,
    owner: Annotated[str | None, typer.Option(help="Filter by owner")] = None,
    include_deleted: Annotated[
        bool, typer.Option("--include-deleted", help="Include soft-deleted tasks")
    ] = False,
) -> None:
    """List orchestration tasks."""
    service = _get_service()

    status_enum: OrchestrationTaskStatus | None = None
    if status is not None:
        try:
            status_enum = OrchestrationTaskStatus(status)
        except ValueError:
            console.print(f"[red]Error: Invalid status '{status}'.[/red]")
            console.print(f"  Valid values: {', '.join(s.value for s in OrchestrationTaskStatus)}")
            raise typer.Exit(1) from None

    try:
        tasks = service.list(status=status_enum, owner=owner, include_deleted=include_deleted)
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    if not tasks:
        console.print("No tasks found.")
        return

    table = Table(title="Orchestration Tasks")
    table.add_column("ID", style="cyan", max_width=8)
    table.add_column("Subject", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Owner", style="magenta")
    table.add_column("Created", style="dim")

    for task in tasks:
        table.add_row(
            task.id[:8],
            task.subject,
            task.status.value,
            task.owner or "-",
            _format_timestamp(task.created_at),
        )

    console.print(table)


@app.command("update")
def update_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    subject: Annotated[str | None, typer.Option(help="New subject")] = None,
    description: Annotated[str | None, typer.Option(help="New description")] = None,
    owner: Annotated[str | None, typer.Option(help="New owner")] = None,
) -> None:
    """Update an orchestration task."""
    if subject is None and description is None and owner is None:
        console.print(
            "[red]Error: Provide at least one of --subject, --description, --owner.[/red]"
        )
        raise typer.Exit(1) from None

    service = _get_service()
    try:
        task = service.update(
            task_id=task_id, subject=subject, description=description, owner=owner
        )
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[green]Task updated successfully.[/green]")
    console.print(f"  ID:          {task.id[:8]}...")
    console.print(f"  Subject:     {task.subject}")
    console.print(f"  Status:      {task.status.value}")


@app.command("submit-plan")
def submit_plan(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    plan_file: Annotated[Path, typer.Option(..., help="Path to plan .md file")],
    requester: Annotated[str | None, typer.Option(help="Who is performing this action")] = None,
) -> None:
    """Submit a plan for a task (transitions PENDING -> PLANNING)."""
    try:
        resolved = plan_file.resolve()
        if not resolved.is_file():
            console.print(f"[red]Error: Plan file not found: {plan_file}[/red]")
            raise typer.Exit(1) from None

        plan_text = resolved.read_text(encoding="utf-8")
    except OSError as e:
        console.print(f"[red]Error reading plan file: {e}[/red]")
        raise typer.Exit(1) from None

    if not plan_text.strip():
        console.print("[red]Error: Plan file is empty.[/red]")
        raise typer.Exit(1) from None

    service = _get_service()
    try:
        task = service.submit_plan(
            task_id=task_id, plan_text=plan_text, requested_by=requester or _default_requester()
        )
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[green]Plan submitted successfully.[/green]")
    console.print(f"  ID:      {task.id[:8]}...")
    console.print(f"  Status:  {task.status.value}")


@app.command("approve")
def approve_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    approved_by: Annotated[str, typer.Option(..., help="Approver identity")],
    requester: Annotated[str | None, typer.Option(help="Who is performing this action")] = None,
) -> None:
    """Approve a planned task (transitions PLANNING -> APPROVED)."""
    if not approved_by.strip():
        console.print("[red]Error: --approved-by cannot be empty.[/red]")
        raise typer.Exit(1) from None

    service = _get_service()
    try:
        task = service.approve(
            task_id=task_id,
            approved_by=approved_by.strip(),
            requested_by=requester or _default_requester(),
        )
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[green]Task approved.[/green]")
    console.print(f"  ID:          {task.id[:8]}...")
    console.print(f"  Approved by: {task.approved_by}")
    console.print(f"  Approved at: {_format_timestamp(task.approved_at or 0)}")


@app.command("reject")
def reject_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    requester: Annotated[str | None, typer.Option(help="Who is performing this action")] = None,
) -> None:
    """Reject a planned task (transitions PLANNING -> PENDING)."""
    service = _get_service()
    try:
        task = service.reject(task_id=task_id, requested_by=requester or _default_requester())
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[yellow]Task rejected, returned to PENDING.[/yellow]")
    console.print(f"  ID:     {task.id[:8]}...")
    console.print(f"  Status: {task.status.value}")


@app.command("start")
def start_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    owner: Annotated[str, typer.Option(..., help="Owner who starts the task")],
    requester: Annotated[str | None, typer.Option(help="Who is performing this action")] = None,
) -> None:
    """Start an approved task (transitions APPROVED -> IN_PROGRESS)."""
    service = _get_service()
    try:
        task = service.start(
            task_id=task_id, owner=owner, requested_by=requester or _default_requester()
        )
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[green]Task started.[/green]")
    console.print(f"  ID:     {task.id[:8]}...")
    console.print(f"  Owner:  {task.owner}")
    console.print(f"  Status: {task.status.value}")


@app.command("complete")
def complete_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    requester: Annotated[str | None, typer.Option(help="Who is performing this action")] = None,
) -> None:
    """Complete an in-progress task (transitions IN_PROGRESS -> COMPLETED)."""
    service = _get_service()
    try:
        task = service.complete(task_id=task_id, requested_by=requester or _default_requester())
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[green]Task completed.[/green]")
    console.print(f"  ID:     {task.id[:8]}...")
    console.print(f"  Status: {task.status.value}")


@app.command("delete")
def delete_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    requester: Annotated[str | None, typer.Option(help="Who is performing this action")] = None,
) -> None:
    """Soft-delete a task (any status -> DELETED)."""
    service = _get_service()
    try:
        task = service.delete(task_id=task_id, requested_by=requester or _default_requester())
    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None

    console.print("[dim]Task deleted.[/dim]")
    console.print(f"  ID:     {task.id[:8]}...")
    console.print(f"  Status: {task.status.value}")


@app.command("assign")
def assign_task(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    to_agent: Annotated[str, typer.Option("--to-agent", help="Target agent name")] = "poll-agent",
) -> None:
    """Assign an approved task to an agent via inbox message."""
    from src.infrastructure.persistence.container import get_task_board_service

    task_svc = get_task_board_service()
    try:
        task = task_svc.get(task_id)
        if task is None:
            console.print(f"[red]Error: Task '{task_id}' not found.[/red]")
            raise typer.Exit(1) from None

        from src.domain.entities.orchestration_task import OrchestrationTaskStatus
        if task.status != OrchestrationTaskStatus.APPROVED:
            console.print(f"[red]Error: Task is {task.status.value}, must be APPROVED to assign.[/red]")
            raise typer.Exit(1) from None

        # Send assignment message via message CLI
        import json

        from src.domain.entities.message import AgentMessage, MessageType
        from src.infrastructure.persistence.container import get_database_connection
        from src.infrastructure.persistence.repositories.message_repository import (
            SqliteMessageRepository,
        )

        db = get_database_connection()
        msg_repo = SqliteMessageRepository(connection=db)
        payload = json.dumps({
            "task_id": task_id,
            "task_subject": task.subject,
            "assigned_by": "cli",
        })
        msg = AgentMessage.create(
            from_agent="cli",
            to_agent=to_agent,
            message_type=MessageType.COMMAND,
            payload=payload,
        )
        msg_repo.save(msg)

    except (ValueError, RepositoryError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected: {e}[/red]")
        raise typer.Exit(1) from None

    console.print(f"[green]Task {task_id[:8]}... assigned to {to_agent}.[/green]")
