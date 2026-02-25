"""Concrete specification implementations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.application.services.orchestration.events import (
    FileWrittenEvent,
    SessionStartEvent,
    SubagentStartEvent,
    SubagentStopEvent,
    ToolPreExecutionEvent,
    UserCommandEvent,
)
from src.domain.ports.event_ports import Event


@dataclass(frozen=True)
class EventTypeSpec:
    """Matches events by their type.

    Uses isinstance() for type checking, compatible with @runtime_checkable Protocols.

    Attributes:
        event_type: The event class to match against.
    """

    event_type: type[Event]

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if event is of the specified type.

        Args:
            event: The event to check.

        Returns:
            True if event is an instance of the specified type.
        """
        return isinstance(event, self.event_type)


@dataclass(frozen=True)
class CommandNameSpec:
    """Matches UserCommandEvent by command name pattern.

    Attributes:
        name_pattern: Regex pattern to match against command_name.
    """

    name_pattern: str

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if event matches the command name pattern.

        Args:
            event: The event to check.

        Returns:
            True if event is UserCommandEvent and command_name matches pattern.
        """
        if not isinstance(event, UserCommandEvent):
            return False
        return bool(re.search(self.name_pattern, event.command_name))


@dataclass(frozen=True)
class FilePathSpec:
    """Matches FileWrittenEvent by path pattern.

    Attributes:
        path_pattern: Regex pattern to match against file path.
    """

    path_pattern: str

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if event matches the path pattern.

        Args:
            event: The event to check.

        Returns:
            True if event is FileWrittenEvent and path matches pattern.
        """
        if not isinstance(event, FileWrittenEvent):
            return False
        return bool(re.search(self.path_pattern, event.path))


@dataclass(frozen=True)
class RegexMatcherSpec:
    """Generic regex matcher compatible with claudikins-kernel hooks.json format.

    Matches events by type name and field value using regex.
    Event type names follow convention: "UserCommand" matches UserCommandEvent.

    Attributes:
        event_type: Event type name without "Event" suffix (e.g., "UserCommand").
        matcher: Regex pattern to match against the relevant field.
    """

    event_type: str
    matcher: str

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if event matches the type and pattern.

        Args:
            event: The event to check.

        Returns:
            True if event type matches and field value matches pattern.
        """
        event_type_name = type(event).__name__.replace("Event", "")
        if event_type_name != self.event_type:
            return False

        pattern = re.compile(self.matcher)

        if isinstance(event, UserCommandEvent):
            return bool(pattern.search(event.command_name))
        if isinstance(event, FileWrittenEvent):
            return bool(pattern.search(event.path))
        if isinstance(event, ToolPreExecutionEvent):
            return bool(pattern.search(event.tool_name))
        if isinstance(event, SessionStartEvent):
            return bool(pattern.search(event.session_id))
        if isinstance(event, SubagentStartEvent):
            return bool(pattern.search(event.agent_name))
        if isinstance(event, SubagentStopEvent):
            return bool(pattern.search(event.agent_name))

        return False
