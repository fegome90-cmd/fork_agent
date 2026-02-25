"""CLI commands for inter-agent messaging using Click.

This module provides CLI commands for sending messages between tmux sessions.
"""

from __future__ import annotations

import sys

import click

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.application.services.messaging.message_protocol import create_command
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


def _create_messenger() -> AgentMessenger:
    """Create an AgentMessenger instance with default configuration.

    Returns:
        Configured AgentMessenger instance.
    """
    orchestrator = TmuxOrchestrator(safety_mode=False)
    store = MessageStore()
    return AgentMessenger(orchestrator=orchestrator, store=store)


@click.group()
def message() -> None:
    """Inter-agent messaging commands.

    Send and manage messages between tmux sessions.

    Examples:
        fork message send agent1:0 "Hello"
        fork message broadcast "Status update"
        fork message list --agent agent1:0
        fork message history agent1:0
    """
    pass


@message.command()
@click.argument("to")
@click.argument("payload")
@click.option(
    "--from",
    "from_agent",
    default="cli:0",
    help="Source agent (session:window format)",
)
def send(to: str, payload: str, from_agent: str) -> None:
    """Send a message to a specific agent.

    TO is the target agent in session:window format (e.g., "agent1:0").

    PAYLOAD is the message content to send.

    Examples:
        fork message send agent1:0 "Hello from CLI"
        fork message send worker:0 '{"task": "analyze"}' --from leader:0
    """
    try:
        messenger = _create_messenger()
        msg = create_command(
            from_=from_agent,
            to=to,
            command=payload,
        )

        success = messenger.send(msg)

        if success:
            click.echo(f"Message sent to {to}")
        else:
            click.echo(f"Failed to send message to {to}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@message.command()
@click.argument("payload")
@click.option(
    "--from",
    "from_agent",
    default="cli:0",
    help="Source agent (session:window format)",
)
def broadcast(payload: str, from_agent: str) -> None:
    """Broadcast a message to all active sessions.

    PAYLOAD is the message content to broadcast.

    Examples:
        fork message broadcast "Status update"
        fork message broadcast "Alert!" --from monitor:0
    """
    try:
        messenger = _create_messenger()
        count = messenger.broadcast(from_agent=from_agent, payload=payload)

        click.echo(f"Broadcast sent to {count} session(s)")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@message.command("list")
@click.option(
    "--agent",
    "-a",
    default=None,
    help="Target agent (session:window format). If not specified, shows recent messages from store.",
)
@click.option(
    "--limit",
    "-l",
    default=10,
    help="Maximum number of messages to show",
)
def list_(agent: str | None, limit: int) -> None:
    """List messages for a specific agent or recent messages.

    Shows messages addressed to the specified agent, or recent messages
    if no agent is specified.

    Examples:
        fork message list
        fork message list --agent agent1:0
        fork message list -a worker:0 -l 20
    """
    try:
        messenger = _create_messenger()

        if agent:
            messages = messenger.get_messages(agent, limit=limit)
        else:
            # Get recent messages from store directly
            messages = messenger.store.get_for_agent("*", limit=limit)

        if not messages:
            if agent:
                click.echo(f"No messages for {agent}")
            else:
                click.echo("No recent messages")
            return

        target = agent or "all"
        click.echo(f"Messages for {target} ({len(messages)}):\n")

        for msg in messages:
            type_str = msg.message_type.name
            click.echo(f"  [{type_str}] {msg.from_agent} -> {msg.to_agent}")
            click.echo(f"    {msg.payload[:100]}{'...' if len(msg.payload) > 100 else ''}")
            click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@message.command()
@click.argument("agent")
@click.option(
    "--limit",
    "-l",
    default=20,
    help="Maximum number of messages to show",
)
def history(agent: str, limit: int) -> None:
    """Show message history for an agent (sent and received).

    AGENT is the agent identifier in session:window format.

    Examples:
        fork message history agent1:0
        fork message history worker:0 --limit 50
    """
    try:
        messenger = _create_messenger()
        messages = messenger.get_history(agent, limit=limit)

        if not messages:
            click.echo(f"No message history for {agent}")
            return

        click.echo(f"Message history for {agent} ({len(messages)}):\n")

        for msg in messages:
            type_str = msg.message_type.name
            direction = "->" if msg.from_agent == agent else "<-"
            other = msg.to_agent if msg.from_agent == agent else msg.from_agent

            click.echo(f"  [{type_str}] {direction} {other}")
            click.echo(f"    {msg.payload[:100]}{'...' if len(msg.payload) > 100 else ''}")
            click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Entry point for direct execution
def run_messaging_cli() -> int:
    """Run the messaging CLI.

    Returns:
        Exit code.
    """
    message()
    return 0


if __name__ == "__main__":
    sys.exit(run_messaging_cli())
