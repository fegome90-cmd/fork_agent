"""CLI commands for inter-agent messaging."""

from __future__ import annotations

from typing import Annotated
import typer
from rich.console import Console
from rich.table import Table

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.container import get_agent_messenger

app = typer.Typer(help="Manage inter-agent messaging.")
console = Console()

@app.command("send")
def send_message(
    to_agent: Annotated[str, typer.Argument(help="Target agent (session:window)")],
    payload: Annotated[str, typer.Argument(help="Message content")],
    from_agent: Annotated[str, typer.Option(help="Source agent ID")] = "cli:0",
    type: Annotated[str, typer.Option("--type", help="Message type (COMMAND/EVENT/OBSERVATION)")] = "COMMAND"
) -> None:

    """Send a message to another agent."""
    messenger = get_agent_messenger()
    
    try:
        mtype = MessageType[type.upper()]
    except KeyError:
        console.print(f"[red]Error: Invalid message type {type}[/red]")
        raise typer.Exit(1)


    msg = AgentMessage.create(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=mtype,
        payload=payload
    )
    
    if messenger.send(msg):
        console.print(f"[green]Message sent successfully to {to_agent}[/green]")
    else:
        console.print(f"[red]Failed to send message via tmux[/red] (stored in history)")

@app.command("broadcast")
def broadcast_message(
    payload: Annotated[str, typer.Argument(help="Message content")],
    from_agent: Annotated[str, typer.Option(help="Source agent ID")] = "cli:0"
) -> None:
    """Send a message to all active tmux sessions."""
    messenger = get_agent_messenger()
    count = messenger.broadcast(from_agent=from_agent, payload=payload)
    console.print(f"[green]Broadcast sent to {count} windows.[/green]")


@app.command("cleanup")
def cleanup_messages(
    max_age: Annotated[int, typer.Option(help="Remove files older than N seconds")] = 300
) -> None:
    """Cleanup expired messages from DB and temp files."""
    from src.application.services.messaging.message_protocol import cleanup_temp_files
    messenger = get_agent_messenger()
    
    # 1. Clean DB
    db_count = messenger.store.cleanup_expired()
    # 2. Clean /tmp
    fs_count = cleanup_temp_files(max_age_seconds=max_age)
    
    console.print(f"[green]Cleanup complete:[/green]")
    console.print(f" - Database: {db_count} messages removed")
    console.print(f" - Filesystem: {fs_count} files removed")


@app.command("history")


def show_history(
    agent_id: Annotated[str, typer.Argument(help="Agent ID to show history for")],
    limit: Annotated[int, typer.Option(help="Max messages to show")] = 20
) -> None:

    """Show message history for an agent."""
    messenger = get_agent_messenger()
    history = messenger.get_history(agent_id, limit=limit)
    
    if not history:
        console.print(f"No messages found for {agent_id}")
        return

    table = Table(title=f"Message History for {agent_id}")
    table.add_column("Date", style="cyan")
    table.add_column("From", style="magenta")
    table.add_column("To", style="magenta")
    table.add_column("Type", style="yellow")
    table.add_column("Payload")

    for msg in history:
        table.add_row(
            msg.created_at_iso,
            msg.from_agent,
            msg.to_agent,
            msg.message_type.name,
            msg.payload[:50] + ("..." if len(msg.payload) > 50 else "")
        )
    
    console.print(table)
