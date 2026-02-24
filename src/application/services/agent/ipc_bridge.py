from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class Message:
    msg_type: MessageType
    sender: str
    recipient: str
    payload: dict[str, Any]
    message_id: str
    timestamp: float
    correlation_id: str | None = None


class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        delay = self._base_delay * (self._exponential_base**attempt)
        return min(delay, self._max_delay)


class IPCBridge:
    def __init__(
        self,
        agent_name: str,
        max_retries: int = 3,
        timeout: float = 30.0,
    ) -> None:
        self._agent_name = agent_name
        self._max_retries = max_retries
        self._timeout = timeout
        self._retry_strategy = RetryStrategy()
        self._inbox: queue.Queue[Message] = queue.Queue()
        self._outbox: queue.Queue[Message] = queue.Queue()
        self._handlers: dict[str, Callable[[Message], None]] = {}
        self._pending_requests: dict[str, queue.Queue[Message]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._worker_thread = threading.Thread(target=self._message_loop, daemon=True)
        self._worker_thread.start()
        logger.info(f"IPCBridge started for agent {self._agent_name}")

    def stop(self) -> None:
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info(f"IPCBridge stopped for agent {self._agent_name}")

    def register_handler(self, msg_type: MessageType, handler: Callable[[Message], None]) -> None:
        with self._lock:
            self._handlers[msg_type.value] = handler

    def send_message(
        self,
        recipient: str,
        payload: dict[str, Any],
        msg_type: MessageType = MessageType.REQUEST,
    ) -> bool:
        message = Message(
            msg_type=msg_type,
            sender=self._agent_name,
            recipient=recipient,
            payload=payload,
            message_id=f"{self._agent_name}-{int(time.time() * 1000)}",
            timestamp=time.time(),
        )

        for attempt in range(self._max_retries):
            try:
                self._outbox.put(message, timeout=self._timeout)
                logger.debug(f"Message sent to {recipient}: {message.message_id}")
                return True
            except queue.Full:
                delay = self._retry_strategy.get_delay(attempt)
                logger.warning(
                    f"Failed to send message, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})"
                )
                time.sleep(delay)

        logger.error(f"Failed to send message to {recipient} after {self._max_retries} retries")
        return False

    def send_request_with_response(
        self,
        recipient: str,
        payload: dict[str, Any],
    ) -> Message | None:
        request_id = f"{self._agent_name}-{int(time.time() * 1000)}"
        request = Message(
            msg_type=MessageType.REQUEST,
            sender=self._agent_name,
            recipient=recipient,
            payload=payload,
            message_id=request_id,
            timestamp=time.time(),
            correlation_id=request_id,
        )

        response_queue: queue.Queue[Message] = queue.Queue()
        with self._lock:
            self._pending_requests[request_id] = response_queue

        try:
            self._outbox.put(request, timeout=self._timeout)

            try:
                response = response_queue.get(timeout=self._timeout)
                return response
            except queue.Empty:
                logger.warning(f"Request {request_id} timed out after {self._timeout}s")
                return None

        finally:
            with self._lock:
                self._pending_requests.pop(request_id, None)

    def receive_message(self, message: Message) -> None:
        self._route_incoming(message)

    def _route_incoming(self, message: Message) -> None:
        # Use correlation_id for response matching if available
        response_key = message.correlation_id
        if response_key is None:
            # Fallback: derive from message_id if it ends with -response
            if message.message_id.endswith("-response"):
                response_key = message.message_id[:-9]  # Strip "-response" suffix
            else:
                response_key = message.message_id

        with self._lock:
            response_queue = self._pending_requests.get(response_key)

        if response_queue is not None:
            try:
                response_queue.put_nowait(message)
                return
            except queue.Full:
                logger.warning(f"Response queue full for request {response_key}")

        # Non-matching message: put in inbox for later processing
        # Don't call _process_incoming here - let the consumer handle it
        self._inbox.put(message, timeout=1.0)

    def broadcast(self, payload: dict[str, Any], recipients: list[str]) -> dict[str, bool]:
        results = {}
        for recipient in recipients:
            results[recipient] = self.send_message(recipient, payload)
        return results

    def _message_loop(self) -> None:
        while self._running:
            try:
                try:
                    message = self._outbox.get(timeout=1.0)
                    self._process_outgoing(message)
                except queue.Empty:
                    continue
            except Exception as e:
                logger.exception(f"Error in message loop: {e}")

    def _process_outgoing(self, message: Message) -> None:
        logger.debug(f"Processing outgoing message: {message.message_id} to {message.recipient}")

    def _process_incoming(self, message: Message) -> None:
        logger.debug(f"Processing incoming message: {message.message_id} from {message.sender}")

        handler = self._handlers.get(message.msg_type.value)
        if handler:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.msg_type.value}: {e}")


class DeadLetterQueue:
    def __init__(self, max_size: int = 1000) -> None:
        self._queue: queue.Queue[tuple[Message, str]] = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()

    def add(self, message: Message, reason: str) -> None:
        try:
            self._queue.put_nowait((message, reason))
            logger.warning(f"Message {message.message_id} added to DLQ: {reason}")
        except queue.Full:
            logger.error(f"DLQ full, dropping message {message.message_id}")

    def get(self, timeout: float = 5.0) -> tuple[Message, str] | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def size(self) -> int:
        return self._queue.qsize()
