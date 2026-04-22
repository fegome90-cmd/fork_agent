"""Lightweight API-key based token verifier for MCP SSE/HTTP transports.

Implements the ``mcp.server.auth.provider.TokenVerifier`` protocol so it
plugs into FastMCP's ``BearerAuthBackend`` without needing a full OAuth
provider.  Only active for SSE/HTTP transports — stdio is always local/trusted.
"""

from __future__ import annotations

import hmac
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.auth.provider import AccessToken

logger = logging.getLogger("memory-mcp")


class ApiKeyTokenVerifier:
    """Validates Bearer tokens against ``FORK_MCP_TOKEN`` env var.

    Returns an ``AccessToken`` when the token matches (constant-time
    comparison via ``hmac.compare_digest``).  Returns ``None`` when
    the token is missing or invalid, which causes ``BearerAuthBackend``
    to treat the request as unauthenticated.

    If ``FORK_MCP_TOKEN`` is not set, every token is accepted — useful
    for local development.
    """

    def __init__(self) -> None:
        import os

        self._expected_token: str = os.environ.get("FORK_MCP_TOKEN", "")
        if not self._expected_token:
            logger.debug("FORK_MCP_TOKEN not set — SSE/HTTP auth disabled")

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a bearer token and return access info if valid."""
        from mcp.server.auth.provider import AccessToken

        if not self._expected_token:
            # No token configured — accept everything.
            return AccessToken(token="*", client_id="local", scopes=[])

        if not hmac.compare_digest(token, self._expected_token):
            return None

        return AccessToken(token=token, client_id="api-key", scopes=[])


__all__ = ["ApiKeyTokenVerifier"]
