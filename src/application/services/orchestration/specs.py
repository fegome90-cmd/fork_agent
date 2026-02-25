"""Concrete specification implementations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import cached_property
from typing import Protocol, runtime_checkable

from src.domain.ports.event_ports import Event

logger = logging.getLogger(__name__)


@runtime_checkable
class _HasPlanId(Protocol):
    """Protocol for events with plan_id field."""
    plan_id: str


@runtime_checkable
class _HasSessionId(Protocol):
    """Protocol for events with session_id field."""
    session_id: str


@runtime_checkable
class _HasAgentName(Protocol):
    """Protocol for events with agent_name field."""
    agent_name: str


@runtime_checkable
class _HasCommandName(Protocol):
    """Protocol for events with command_name field."""
    command_name: str


@runtime_checkable
class _HasPath(Protocol):
    """Protocol for events with path field."""
    path: str


@runtime_checkable
class _HasToolName(Protocol):
    """Protocol for events with tool_name field."""
    tool_name: str


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

    @cached_property
    def _pattern(self) -> re.Pattern[str]:
        """Compiled regex pattern."""
        return re.compile(self.name_pattern)

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if event matches the command name pattern.

        Args:
            event: The event to check.

        Returns:
            True if event is UserCommandEvent and command_name matches pattern.
        """
        if isinstance(event, _HasCommandName):
            return bool(self._pattern.search(event.command_name))
        return False


@dataclass(frozen=True)
class FilePathSpec:
    """Matches FileWrittenEvent by path pattern.

    Attributes:
        path_pattern: Regex pattern to match against file path.
    """

    path_pattern: str

    @cached_property
    def _pattern(self) -> re.Pattern[str]:
        """Compiled regex pattern."""
        return re.compile(self.path_pattern)

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if event matches the path pattern.

        Args:
            event: The event to check.

        Returns:
            True if event is FileWrittenEvent and path matches pattern.
        """
        if isinstance(event, _HasPath):
            return bool(self._pattern.search(event.path))
        return False


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

    @cached_property
    def _pattern(self) -> re.Pattern[str]:
        """Compiled regex pattern with error handling."""
        try:
            return re.compile(self.matcher)
        except re.error:
            logger.warning("Invalid regex pattern '%s', using match-all", self.matcher)
            return re.compile(".*")

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

        # Use protocol-based matching to extract the relevant field
        if isinstance(event, _HasPlanId):
            return bool(self._pattern.search(event.plan_id))
        if isinstance(event, _HasSessionId):
            return bool(self._pattern.search(event.session_id))
        if isinstance(event, _HasAgentName):
            return bool(self._pattern.search(event.agent_name))
        if isinstance(event, _HasCommandName):
            return bool(self._pattern.search(event.command_name))
        if isinstance(event, _HasPath):
            return bool(self._pattern.search(event.path))
        if isinstance(event, _HasToolName):
            return bool(self._pattern.search(event.tool_name))

        return False
