"""Ports (Protocols) for event-driven hook orchestration."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Event(Protocol):
    """Marker protocol for system events.

    Empty protocol used for type narrowing with isinstance() checks
    in concrete specification implementations.
    """

    ...


@runtime_checkable
class Action(Protocol):
    """Marker protocol for executable actions.

    Empty protocol used for type narrowing with isinstance() checks
    in action runner implementations.
    """

    ...


class ISpecification(Protocol):
    """Specification pattern for matching events to rules.

    Determines if an event satisfies the criteria for a rule to apply.
    Concrete implementations use isinstance() narrowing with Event protocol.
    """

    def is_satisfied_by(self, event: Event) -> bool:
        """Check if the event satisfies this specification.

        Args:
            event: The event to evaluate.

        Returns:
            True if the event matches the specification criteria.
        """
        ...


class IActionRunner(Protocol):
    """Port for executing actions.

    Separates orchestration logic from side effects.
    Infrastructure layer provides concrete implementations.
    """

    def run(self, action: Action) -> None:
        """Execute the given action.

        Args:
            action: The action to execute.
        """
        ...
