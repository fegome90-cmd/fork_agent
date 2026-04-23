"""CLI commands for inter-agent messaging."""

from __future__ import annotations

import json
import os
import time
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.container import get_agent_messenger

app = typer.Typer(help="Manage inter-agent messaging.")
console = Console()


@app.command("send")
def send_message(
    to_agent: Annotated[str, typer.Argument(help="Target agent (session:window)")],
    payload: Annotated[str, typer.Argument(help="Message content")],
    from_agent: Annotated[str, typer.Option(help="Source agent ID")] = "cli:0",
    type: Annotated[
        str,
        typer.Option(
            "--type", help="Message type (COMMAND/REPLY/HANDOFF/PROGRESS/FILE_TOUCHED/OBSERVATION)"
        ),
    ] = "COMMAND",
) -> None:
    """Send a message to another agent."""
    if os.environ.get("FORK_HYBRID") == "1":
        from src.infrastructure.persistence.container import get_memory_service_auto
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(get_memory_service_auto())
        result, _receipt = dispatcher.dispatch_message_send(
            to_agent=to_agent, payload=payload, from_agent=from_agent, type=type
        )
        console.print(f"[green]Message sent successfully to {to_agent}[/green]")
        return

    messenger = get_agent_messenger()

    try:
        mtype = MessageType[type.upper()]
    except KeyError:
        console.print(f"[red]Error: Invalid message type {type}[/red]")
        raise typer.Exit(1)  # noqa: B904
    msg = AgentMessage.create(
        from_agent=from_agent, to_agent=to_agent, message_type=mtype, payload=payload
    )

    if messenger.send(msg):
        console.print(f"[green]Message sent successfully to {to_agent}[/green]")
    else:
        console.print("[red]Failed to send message via tmux[/red] (stored in history)")


@app.command("broadcast")
def broadcast_message(
    payload: Annotated[str, typer.Argument(help="Message content")],
    from_agent: Annotated[str, typer.Option(help="Source agent ID")] = "cli:0",
) -> None:
    """Send a message to all active tmux sessions."""
    if os.environ.get("FORK_HYBRID") == "1":
        from src.infrastructure.persistence.container import get_memory_service_auto
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(get_memory_service_auto())
        result, _receipt = dispatcher.dispatch_message_broadcast(
            payload=payload, from_agent=from_agent
        )
        console.print("[green]Broadcast sent.[/green]")
        return

    messenger = get_agent_messenger()
    count = messenger.broadcast(from_agent=from_agent, payload=payload)
    console.print(f"[green]Broadcast sent to {count} windows.[/green]")


@app.command("cleanup")
def cleanup_messages(
    max_age: Annotated[int, typer.Option(help="Remove files older than N seconds")] = 300,
) -> None:
    """Cleanup expired messages from DB and temp files."""
    if os.environ.get("FORK_HYBRID") == "1":
        from src.infrastructure.persistence.container import get_memory_service_auto
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(get_memory_service_auto())
        result, _receipt = dispatcher.dispatch_message_cleanup(max_age=max_age)
        console.print(f"[green]Cleanup complete:[/green] {result}")
        return

    from src.application.services.messaging.message_protocol import cleanup_temp_files

    messenger = get_agent_messenger()

    # 1. Clean DB
    db_count = messenger.store.cleanup_expired()
    # 2. Clean /tmp
    fs_count = cleanup_temp_files(max_age_seconds=max_age)

    console.print("[green]Cleanup complete:[/green]")
    console.print(f" - Database: {db_count} messages removed")
    console.print(f" - Filesystem: {fs_count} files removed")


@app.command("history")
def show_history(
    agent_id: Annotated[str, typer.Argument(help="Agent ID to show history for")],
    limit: Annotated[int, typer.Option(help="Max messages to show")] = 20,
) -> None:
    """Show message history for an agent."""
    if os.environ.get("FORK_HYBRID") == "1":
        from src.infrastructure.persistence.container import get_memory_service_auto
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(get_memory_service_auto())
        result, _receipt = dispatcher.dispatch_message_history(agent_id=agent_id, limit=limit)
        if not result:
            console.print(f"No messages found for {agent_id}")
            return
        table = Table(title=f"Message History for {agent_id}")
        table.add_column("Date", style="cyan")
        table.add_column("From", style="magenta")
        table.add_column("To", style="magenta")
        table.add_column("Type", style="yellow")
        table.add_column("Payload")
        for msg in result:
            if isinstance(msg, dict):
                table.add_row(
                    str(msg.get("created_at", "")),
                    str(msg.get("from_agent", "")),
                    str(msg.get("to_agent", "")),
                    str(msg.get("message_type", "")),
                    str(msg.get("payload", ""))[:50],
                )
        console.print(table)
        return

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
            msg.payload[:50] + ("..." if len(msg.payload) > 50 else ""),
        )

    console.print(table)


@app.command("receive")
def receive_messages(
    agent_id: Annotated[
        str, typer.Argument(help="Agent ID to receive messages for (session:window)")
    ],
    limit: Annotated[int, typer.Option(help="Max messages to retrieve")] = 10,
    watch: Annotated[
        bool, typer.Option("--watch", help="Continuous polling (5s interval)")
    ] = False,
    mark_read: Annotated[
        bool, typer.Option("--mark-read", help="Delete messages after retrieval")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    # Hybrid dispatch (non-watch only — watch polling not suitable for MCP)
    if os.environ.get("FORK_HYBRID") == "1" and not watch:
        from src.infrastructure.persistence.container import get_memory_service_auto
        from src.interfaces.cli.hybrid import HybridDispatcher

        dispatcher = HybridDispatcher(get_memory_service_auto())
        result, _receipt = dispatcher.dispatch_message_receive(
            agent_id=agent_id, limit=limit, mark_read=mark_read
        )
        if not result:
            console.print(f"No messages for {agent_id}")
            return
        if json_output:
            console.print_json(json.dumps(result, indent=2))
            return
        for msg in result:
            console.print(
                f"[cyan]{getattr(msg, 'id', msg)}[/cyan] from [magenta]{getattr(msg, 'from_agent', '?')}[/magenta]: {getattr(msg, 'payload', msg)}"
            )
        return

    messenger = get_agent_messenger()

    def _fetch() -> list[AgentMessage]:
        return messenger.get_messages(agent_id, limit=limit)

    def _print_messages(msgs: list[AgentMessage]) -> None:
        if json_output:
            output = [
                {
                    "id": msg.id,
                    "from": msg.from_agent,
                    "to": msg.to_agent,
                    "type": msg.message_type.name,
                    "payload": msg.payload,
                    "created_at": msg.created_at_iso,
                }
                for msg in msgs
            ]
            print(json.dumps(output, indent=2))
        else:
            if not msgs:
                console.print(f"No messages for {agent_id}")
                return
            table = Table(title=f"Inbox for {agent_id}")
            table.add_column("Date", style="cyan")
            table.add_column("From", style="magenta")
            table.add_column("Type", style="yellow")
            table.add_column("Payload")
            for msg in msgs:
                table.add_row(
                    msg.created_at_iso,
                    msg.from_agent,
                    msg.message_type.name,
                    msg.payload[:50] + ("..." if len(msg.payload) > 50 else ""),
                )
            console.print(table)

    def _delete_messages(msgs: list[AgentMessage]) -> None:
        if not msgs:
            return
        ids = [msg.id for msg in msgs]
        messenger.store.delete_by_ids(ids)

    if not watch:
        messages = _fetch()
        _print_messages(messages)
        if mark_read:
            _delete_messages(messages)
        return

    # Watch mode
    console.print(f"[dim]Watching inbox for {agent_id}... (Ctrl+C to stop)[/dim]")
    try:
        while True:
            console.clear()
            messages = _fetch()
            console.print(f"[dim]{len(messages)} message(s) for {agent_id}[/dim]")
            _print_messages(messages)
            if mark_read:
                _delete_messages(messages)
            time.sleep(5)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching.[/dim]")
