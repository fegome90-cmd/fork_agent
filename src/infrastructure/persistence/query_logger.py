"""Query logging utility for performance monitoring."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class QueryLogger:
    """Logger for tracking slow database queries."""

    def __init__(self, threshold_ms: float = 100.0) -> None:
        """Initialize query logger.

        Args:
            threshold_ms: Time in milliseconds above which queries are logged.
        """
        self._threshold_ms = threshold_ms
        self._slow_queries: list[dict[str, Any]] = []

    @property
    def threshold_ms(self) -> float:
        """Get the threshold in milliseconds."""
        return self._threshold_ms

    @threshold_ms.setter
    def threshold_ms(self, value: float) -> None:
        """Set the threshold in milliseconds."""
        self._threshold_ms = value

    def log_query(self, query: str, params: tuple, duration_ms: float) -> None:
        """Log a query execution.

        Args:
            query: The SQL query string.
            params: The query parameters.
            duration_ms: Execution time in milliseconds.
        """
        if duration_ms >= self._threshold_ms:
            entry = {
                "query": query[:200],  # Truncate long queries
                "params": str(params)[:100],
                "duration_ms": duration_ms,
            }
            self._slow_queries.append(entry)
            logger.warning(
                "Slow query detected: %s ms - %s",
                f"{duration_ms:.2f}",
                query[:100],
            )

    def get_slow_queries(self) -> list[dict[str, Any]]:
        """Get list of logged slow queries."""
        return self._slow_queries.copy()

    def clear(self) -> None:
        """Clear the slow query log."""
        self._slow_queries.clear()

    def __len__(self) -> int:
        """Get count of slow queries."""
        return len(self._slow_queries)


# Global query logger instance
_query_logger = QueryLogger()


def get_query_logger() -> QueryLogger:
    """Get the global query logger instance."""
    return _query_logger


def log_query_time(query: str) -> Callable:
    """Decorator to log query execution time.

    Args:
        query: Description of the query for logging.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                _query_logger.log_query(query, (), duration_ms)

        return wrapper

    return decorator
