"""Tests for ApiKeyTokenVerifier."""

from __future__ import annotations

import os

import pytest

from src.interfaces.mcp.auth import ApiKeyTokenVerifier


class TestApiKeyTokenVerifier:
    """Tests for the lightweight API-key token verifier."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Remove FORK_MCP_TOKEN before each test for isolation."""
        monkeypatch.delenv("FORK_MCP_TOKEN", raising=False)

    @pytest.mark.asyncio
    async def test_matching_token_returns_access_token(self) -> None:
        os.environ["FORK_MCP_TOKEN"] = "secret-key-123"
        verifier = ApiKeyTokenVerifier()
        result = await verifier.verify_token("secret-key-123")
        assert result is not None
        assert result.client_id == "api-key"
        assert result.token == "secret-key-123"

    @pytest.mark.asyncio
    async def test_wrong_token_returns_none(self) -> None:
        os.environ["FORK_MCP_TOKEN"] = "secret-key-123"
        verifier = ApiKeyTokenVerifier()
        result = await verifier.verify_token("wrong-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_env_var_accepts_anything(self) -> None:
        os.environ["FORK_MCP_TOKEN"] = ""
        verifier = ApiKeyTokenVerifier()
        result = await verifier.verify_token("anything-goes")
        assert result is not None
        assert result.client_id == "local"

    @pytest.mark.asyncio
    async def test_missing_env_var_accepts_anything(self) -> None:
        verifier = ApiKeyTokenVerifier()
        result = await verifier.verify_token("any-token")
        assert result is not None
        assert result.client_id == "local"

    @pytest.mark.asyncio
    async def test_empty_string_token_rejected_when_configured(self) -> None:
        os.environ["FORK_MCP_TOKEN"] = "secret-key-123"
        verifier = ApiKeyTokenVerifier()
        result = await verifier.verify_token("")
        assert result is None
