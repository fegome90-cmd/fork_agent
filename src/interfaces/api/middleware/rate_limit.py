"""Rate limiting middleware."""

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitEntry:
    """Track requests for a client."""

    requests: list[float] = field(default_factory=list)
    blocked_until: float = 0.0


class InMemoryRateLimiter:
    """Simple in-memory rate limiter with sliding window."""

    def __init__(self, requests_per_minute: int = 100) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self._clients: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> tuple[bool, int, int]:
        """Check if client is allowed to make request.

        Returns:
            (is_allowed, remaining_requests, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()
            entry = self._clients[client_id]

            if now < entry.blocked_until:
                retry_after = int(entry.blocked_until - now)
                return False, 0, retry_after

            entry.requests = [ts for ts in entry.requests if now - ts < self.window_seconds]

            if len(entry.requests) >= self.requests_per_minute:
                entry.blocked_until = now + self.window_seconds
                return False, 0, self.window_seconds

            entry.requests.append(now)
            remaining = self.requests_per_minute - len(entry.requests)
            return True, remaining, 0

    async def cleanup_old_entries(self, max_age: float = 300) -> None:
        """Remove entries older than max_age seconds."""
        async with self._lock:
            now = time.time()
            to_remove = []
            for client_id, entry in self._clients.items():
                if (
                    entry.requests
                    and now - max(entry.requests) > max_age
                    or not entry.requests
                    and now - entry.blocked_until > max_age
                ):
                    to_remove.append(client_id)
            for client_id in to_remove:
                del self._clients[client_id]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        key_func: Callable[[Request], str] | None = None,
        excluded_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = InMemoryRateLimiter(requests_per_minute)
        self.key_func = key_func or self._default_key_func
        self.excluded_paths = excluded_paths or {"/", "/docs", "/openapi.json", "/redoc"}

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Get client identifier from request.

        Priority: X-API-Key > client IP. X-Forwarded-For is NOT trusted
        without a known reverse proxy — using it allows trivial rate limit
        bypass by spoofing the header.
        """
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{hash(api_key)}"

        if request.client:
            return request.client.host

        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        if request.url.path in self.excluded_paths:
            return await call_next(request)  # type: ignore[no-any-return]

        client_id = self.key_func(request)
        is_allowed, remaining, retry_after = await self.limiter.is_allowed(client_id)

        if is_allowed:
            response: Response = await call_next(request)
        else:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                        "details": {
                            "retry_after": retry_after,
                            "limit": self.limiter.requests_per_minute,
                        },
                    },
                },
                headers={
                    "X-RateLimit-Limit": str(self.limiter.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(retry_after),
                    "Retry-After": str(retry_after),
                },
            )

        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if retry_after > 0:
            response.headers["Retry-After"] = str(retry_after)

        return response


rate_limiter = InMemoryRateLimiter()
