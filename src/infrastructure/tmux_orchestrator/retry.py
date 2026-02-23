from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0


@dataclass
class RetryResult:
    success: bool
    result: Any | None
    error: str | None
    attempts: int


class ExponentialBackoff:
    """Exponential backoff calculator for retry operations."""

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
    ) -> None:
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        delay = self._base_delay * (self._exponential_base**attempt)
        return min(delay, self._max_delay)


async def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig | None = None,
    *args: Any,
    **kwargs: Any,
) -> RetryResult:
    """Execute function with exponential backoff retry."""
    if config is None:
        config = RetryConfig()

    backoff = ExponentialBackoff(
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        exponential_base=config.exponential_base,
    )

    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return RetryResult(success=True, result=result, error=None, attempts=attempt + 1)
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

            if attempt < config.max_retries:
                delay = backoff.get_delay(attempt)
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

    return RetryResult(
        success=False,
        result=None,
        error=str(last_error) if last_error else "Unknown error",
        attempts=config.max_retries + 1,
    )


def retry_sync(
    func: Callable[..., T],
    config: RetryConfig | None = None,
    *args: Any,
    **kwargs: Any,
) -> RetryResult:
    """Synchronous version of retry_with_backoff."""
    if config is None:
        config = RetryConfig()

    backoff = ExponentialBackoff(
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        exponential_base=config.exponential_base,
    )

    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            result = func(*args, **kwargs)
            return RetryResult(success=True, result=result, error=None, attempts=attempt + 1)
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

            if attempt < config.max_retries:
                delay = backoff.get_delay(attempt)
                logger.info(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)

    return RetryResult(
        success=False,
        result=None,
        error=str(last_error) if last_error else "Unknown error",
        attempts=config.max_retries + 1,
    )
