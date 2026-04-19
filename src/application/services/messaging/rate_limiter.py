"""Rate limiter for Memory Hook - FASE 3.

Simple sliding window rate limiter in-memory.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimitEntry:
    """Entry for rate limit tracking."""

    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Sliding window rate limiter.

    Tracks request counts per key within a time window.
    """

    def __init__(
        self,
        max_requests: int = 30,
        window_seconds: int = 60,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Window size in seconds
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for key.

        Args:
            key: Rate limit key (e.g., "run_id:task_id:agent_id:message_type")

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        entry = self._entries[key]

        # Remove expired timestamps
        cutoff = now - self._window_seconds
        entry.timestamps = [ts for ts in entry.timestamps if ts > cutoff]

        # Check limit
        if len(entry.timestamps) >= self._max_requests:
            return False

        # Record this request
        entry.timestamps.append(now)
        return True

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit for key or all keys.

        Args:
            key: Key to reset, or None to reset all
        """
        if key is None:
            self._entries.clear()
        elif key in self._entries:
            del self._entries[key]

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for key.

        Args:
            key: Rate limit key

        Returns:
            Number of remaining requests in current window
        """
        now = time.time()
        entry = self._entries.get(key)

        if not entry:
            return self._max_requests

        # Remove expired timestamps
        cutoff = now - self._window_seconds
        active_count = sum(1 for ts in entry.timestamps if ts > cutoff)

        return max(0, self._max_requests - active_count)
