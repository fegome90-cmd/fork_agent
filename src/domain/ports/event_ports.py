"""Ports (Protocols) for event-driven hook orchestration."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


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


class IMessageBroker(Protocol):
    """Port for async pub/sub message broker.

    Decouples publishers from subscribers. Implementations can use
    asyncio queues, Redis pub/sub, or in-memory event buses.
    """

    async def publish(self, topic: str, message: Event) -> None:
        """Publish a message to a topic.

        Args:
            topic: The topic/channel to publish to.
            message: The event or message to publish.
        """
        ...

    async def subscribe(self, topic: str, handler: Any) -> None:
        """Subscribe a handler to a topic.

        Args:
            topic: The topic/channel to subscribe to.
            handler: A callable that accepts the published message.
        """
        ...

    async def unsubscribe(self, topic: str, handler: Any) -> None:
        """Remove a handler subscription.

        Args:
            topic: The topic/channel to unsubscribe from.
            handler: The handler to remove.
        """
        ...

    async def close(self) -> None:
        """Gracefully shut down the broker, draining pending messages."""
        ...
