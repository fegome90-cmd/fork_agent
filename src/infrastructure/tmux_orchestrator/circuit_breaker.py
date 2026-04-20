from __future__ import annotations

import logging
import threading
import time
from enum import Enum

from src.infrastructure.tmux_orchestrator.resilience_policy import (
    DEFAULT_POLICY,
    ResiliencePolicy,
    get_default_policy,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TmuxCircuitBreaker:
    def __init__(
        self,
        policy: ResiliencePolicy | None = None,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
        half_open_max_calls: int | None = None,
    ) -> None:
        if policy is not None:
            p = policy
        elif (
            failure_threshold is not None
            or recovery_timeout is not None
            or half_open_max_calls is not None
        ):
            p = ResiliencePolicy(
                failure_threshold=failure_threshold
                if failure_threshold is not None
                else DEFAULT_POLICY.failure_threshold,
                recovery_timeout_seconds=recovery_timeout
                if recovery_timeout is not None
                else DEFAULT_POLICY.recovery_timeout_seconds,
                half_open_max_calls=half_open_max_calls
                if half_open_max_calls is not None
                else DEFAULT_POLICY.half_open_max_calls,
            )
        else:
            p = get_default_policy()
        self._failure_threshold = p.failure_threshold
        self._recovery_timeout = p.recovery_timeout_seconds
        self._half_open_max_calls = p.half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def policy(self) -> ResiliencePolicy:
        return ResiliencePolicy(
            failure_threshold=self._failure_threshold,
            recovery_timeout_seconds=self._recovery_timeout,
            half_open_max_calls=self._half_open_max_calls,
        )

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if (
                self._state == CircuitState.OPEN
                and time.time() - self._last_failure_time >= self._recovery_timeout
            ):
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
