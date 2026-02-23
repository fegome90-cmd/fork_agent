from __future__ import annotations

import logging
import threading
import time
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TmuxCircuitBreaker:
    """Circuit breaker specifically for tmux operations.

    Tracks failures for tmux operations (spawn, send, capture) and prevents
    cascading failures when tmux becomes unresponsive.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 2,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker OPEN after {self._failure_count} failures")

    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self._half_open_max_calls:
                    self._half_open_calls += 1
                    return True
        return False

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def reset(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
