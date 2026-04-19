"""Schedule command for CLI."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import typer

from src.infrastructure.persistence.container import get_default_db_path
from src.interfaces.cli.dependencies import get_scheduler_service

app = typer.Typer()


@app.command()
def add(
    _ctx: typer.Context,
    action: str = typer.Argument(...),
    delay_seconds: int = typer.Argument(...),
    context: str | None = typer.Option(None, "--context", "-c"),
    db_path: str = typer.Option(str(get_default_db_path()), "--db", "-d"),
) -> None:
    scheduler_service = get_scheduler_service(Path(db_path))
    context_dict = None

    if context:
        try:
            context_dict = json.loads(context)
        except json.JSONDecodeError as e:
            typer.echo("Error: Invalid JSON in context", err=True)
            raise typer.Exit(1) from e

    scheduled_at = int(time.time() * 1000) + (delay_seconds * 1000)
    task_id = uuid.uuid4().hex

    task = scheduler_service.create_task(
        task_id=task_id,
        action=action,
        scheduled_at=scheduled_at,
        context=context_dict,
    )
    typer.echo(f"Scheduled task: {task.id}")
    typer.echo(f"  Action: {task.action}")
    typer.echo(f"  Will execute in {delay_seconds} seconds")


@app.command(name="list")
def list_tasks(
    _ctx: typer.Context,
    db_path: str = typer.Option(str(get_default_db_path()), "--db", "-d"),
) -> None:
    scheduler_service = get_scheduler_service(Path(db_path))
    tasks = scheduler_service.get_pending_tasks()

    if not tasks:
        typer.echo("No pending tasks")
        return

    for task in tasks:
        typer.echo(f"[{task.id}] {task.action} (scheduled at {task.scheduled_at})")


@app.command()
def show(
    _ctx: typer.Context,
    task_id: str = typer.Argument(...),
    db_path: str = typer.Option(str(get_default_db_path()), "--db", "-d"),
) -> None:
    scheduler_service = get_scheduler_service(Path(db_path))
    task = scheduler_service.get_task(task_id)

    if task is None:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Task ID: {task.id}")
    typer.echo(f"Action: {task.action}")
    typer.echo(f"Status: {task.status.value}")
    typer.echo(f"Scheduled at: {task.scheduled_at}")
    typer.echo(f"Created at: {task.created_at}")
    if task.context:
        typer.echo(f"Context: {json.dumps(task.context)}")


@app.command()
def cancel(
    _ctx: typer.Context,
    task_id: str = typer.Argument(...),
    db_path: str = typer.Option(str(get_default_db_path()), "--db", "-d"),
) -> None:
    scheduler_service = get_scheduler_service(Path(db_path))
    task = scheduler_service.get_task(task_id)

    if task is None:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    scheduler_service.cancel_task(task_id)
    typer.echo(f"Cancelled task: {task_id}")
