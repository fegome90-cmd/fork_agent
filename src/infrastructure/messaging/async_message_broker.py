"""Async pub/sub message broker using asyncio.

Replaces synchronous EventDispatcher with an async publish/subscribe
pattern. Subscribers register per-topic handlers; publishers emit
events without knowing who listens.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from src.domain.ports.event_ports import Event, IMessageBroker

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Coroutine[Any, Any, None]]
"""Type alias for an async event handler."""


class InMemoryBroker(IMessageBroker):
    """In-memory async pub/sub broker.

    Topics are strings. Each topic can have multiple handlers.
    Handlers are awaited concurrently on publish.

    Example:
        broker = InMemoryBroker()
        await broker.subscribe("workflow.start", my_handler)
        await broker.publish("workflow.start", WorkflowOutlineStartEvent(...))
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._closed = False

    async def publish(self, topic: str, message: Event) -> None:
        """Publish an event to all handlers subscribed to *topic*.

        Handlers run concurrently via asyncio.gather. If any handler
        raises, it's logged but does NOT cancel other handlers.
        """
        if self._closed:
            logger.warning("Broker closed, dropping message on topic '%s'", topic)
            return

        handlers = self._subscribers.get(topic, [])
        if not handlers:
            logger.debug("No handlers for topic '%s'", topic)
            return

        results = await asyncio.gather(
            *[handler(message) for handler in handlers],
            return_exceptions=True,
        )

        for handler, result in zip(handlers, results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "Handler %s failed on topic '%s': %s",
                    getattr(handler, "__name__", handler),
                    topic,
                    result,
                )

    async def subscribe(self, topic: str, handler: Handler) -> None:
        """Register an async handler for a topic."""
        if self._closed:
            raise RuntimeError("Cannot subscribe to a closed broker")

        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)
            logger.debug("Subscribed %s to topic '%s'", handler.__name__, topic)

    async def unsubscribe(self, topic: str, handler: Handler) -> None:
        """Remove a handler from a topic."""
        try:
            self._subscribers[topic].remove(handler)
            logger.debug("Unsubscribed %s from topic '%s'", handler.__name__, topic)
        except ValueError:
            logger.warning("Handler %s not found for topic '%s'", handler.__name__, topic)

    async def close(self) -> None:
        """Shut down the broker, preventing new publishes/subscribes."""
        self._closed = True
        self._subscribers.clear()
        logger.info("InMemoryBroker closed")
