"""Tests for output cap integration in MCP tool handlers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fake Observation entity (matches domain Observation dataclass shape)
# ---------------------------------------------------------------------------


@dataclass
class FakeObservation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    type: str | None = None
    project: str | None = None
    topic_key: str | None = None
    metadata: dict | None = None
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _make_fake_obs(content: str = "short content", **overrides: Any) -> FakeObservation:
    defaults: dict[str, Any] = {"content": content}
    defaults.update(overrides)
    return FakeObservation(**defaults)


_LARGE_CONTENT = "word " * 20000  # ~100KB, well over 8000 token budget


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_service_singletons():
    """Reset module-level service globals before each test to avoid leakage."""
    import src.interfaces.mcp.tools as tools_mod

    original = (
        tools_mod._memory_service,
        tools_mod._session_service,
        tools_mod._health_service,
    )
    tools_mod._memory_service = None
    tools_mod._session_service = None
    tools_mod._health_service = None
    yield
    tools_mod._memory_service, tools_mod._session_service, tools_mod._health_service = original


def _mock_memory_service(**method_returns: Any) -> MagicMock:
    """Create a mock memory service with specified method return values."""
    service = MagicMock()
    for name, retval in method_returns.items():
        getattr(service, name).return_value = retval
    return service


# ---------------------------------------------------------------------------
# memory_search
# ---------------------------------------------------------------------------


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_search_small_results_no_truncation(mock_get_service: MagicMock):
    """Small results should pass through without capping."""
    obs = _make_fake_obs(content="tiny")
    mock_get_service.return_value = _mock_memory_service(search=[obs])

    from src.interfaces.mcp.tools import memory_search

    result = json.loads(memory_search(query="tiny"))
    assert len(result) == 1
    assert result[0]["content"] == "tiny"
    assert "_truncated" not in result[0]


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_search_max_tokens_1_truncates(mock_get_service: MagicMock):
    """max_tokens should truncate content to fit budget."""
    obs = _make_fake_obs(content=_LARGE_CONTENT)
    mock_get_service.return_value = _mock_memory_service(search=[obs])

    from src.interfaces.mcp.tools import memory_search

    result = json.loads(memory_search(query="big", max_tokens=50))
    assert len(result) >= 1
    # Content should be heavily truncated
    assert len(result[0]["content"]) < len(_LARGE_CONTENT)
    assert result[0].get("_truncated") is True


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_search_default_behavior(mock_get_service: MagicMock):
    """Default (no max_tokens) uses DEFAULT_MAX_TOKENS (8000)."""
    obs = _make_fake_obs(content="normal content")
    mock_get_service.return_value = _mock_memory_service(search=[obs])

    from src.interfaces.mcp.tools import memory_search

    result = json.loads(memory_search(query="normal"))
    assert len(result) == 1
    assert result[0]["content"] == "normal content"


# ---------------------------------------------------------------------------
# memory_get
# ---------------------------------------------------------------------------


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_get_respects_max_tokens(mock_get_service: MagicMock):
    """Large single observation should be truncated when max_tokens is small."""
    obs = _make_fake_obs(content=_LARGE_CONTENT)
    mock_get_service.return_value = _mock_memory_service(get_by_id=obs)

    from src.interfaces.mcp.tools import memory_get

    result = json.loads(memory_get(id=obs.id, max_tokens=50))
    assert result.get("_truncated") is True
    assert len(result["content"]) < len(_LARGE_CONTENT)


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_get_small_content_unchanged(mock_get_service: MagicMock):
    """Small content should pass through without truncation."""
    obs = _make_fake_obs(content="small")
    mock_get_service.return_value = _mock_memory_service(get_by_id=obs)

    from src.interfaces.mcp.tools import memory_get

    result = json.loads(memory_get(id=obs.id))
    assert result["content"] == "small"
    assert "_truncated" not in result


# ---------------------------------------------------------------------------
# memory_list
# ---------------------------------------------------------------------------


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_list_respects_max_tokens(mock_get_service: MagicMock):
    """List with large observations should respect max_tokens budget."""
    observations = [_make_fake_obs(content=_LARGE_CONTENT) for _ in range(5)]
    mock_get_service.return_value = _mock_memory_service(get_recent=observations)

    from src.interfaces.mcp.tools import memory_list

    result = json.loads(memory_list(limit=5, max_tokens=50))
    # With a tiny budget, most observations should be dropped
    assert len(result) < 5


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_list_default_no_truncation_for_small(mock_get_service: MagicMock):
    """Small list should pass through without capping by default."""
    observations = [_make_fake_obs(content="item") for _ in range(3)]
    mock_get_service.return_value = _mock_memory_service(get_recent=observations)

    from src.interfaces.mcp.tools import memory_list

    result = json.loads(memory_list(limit=3))
    assert len(result) == 3
    assert all("_truncated" not in r for r in result)


# ---------------------------------------------------------------------------
# memory_context
# ---------------------------------------------------------------------------


@patch("src.interfaces.mcp.tools._get_memory_service")
def test_memory_context_respects_max_tokens(mock_get_service: MagicMock):
    """Context with large observations should respect max_tokens budget."""
    observations = [_make_fake_obs(content=_LARGE_CONTENT)]
    mock_get_service.return_value = _mock_memory_service(get_recent=observations)

    from src.interfaces.mcp.tools import memory_context

    result = json.loads(memory_context(limit=1, max_tokens=50))
    assert len(result) >= 1
    assert result[0].get("_truncated") is True
