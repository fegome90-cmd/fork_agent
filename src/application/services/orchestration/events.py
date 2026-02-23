"""Concrete event implementations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserCommandEvent:
    """Event fired when user invokes a CLI command.

    Attributes:
        command_name: The name of the command invoked.
        args: Tuple of command arguments.
    """

    command_name: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileWrittenEvent:
    """Event fired when a file is written or modified.

    Attributes:
        path: The absolute path to the file that was written.
    """

    path: str


@dataclass(frozen=True)
class ToolPreExecutionEvent:
    """Event fired before a tool executes.

    Used for PreToolUse hooks to gate or modify tool execution.

    Attributes:
        tool_name: The name of the tool about to execute.
    """

    tool_name: str


@dataclass(frozen=True)
class SessionStartEvent:
    """Event fired when a new session starts."""

    session_id: str = ""


@dataclass(frozen=True)
class SubagentStartEvent:
    """Event fired when a subagent starts.

    Attributes:
        agent_name: Name of the agent starting.
    """

    agent_name: str


@dataclass(frozen=True)
class SubagentStopEvent:
    """Event fired when a subagent stops.

    Attributes:
        agent_name: Name of the agent that stopped.
        duration_ms: Duration in milliseconds.
    """

    agent_name: str
    duration_ms: int = 0
    status: str = "completed"
