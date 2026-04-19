"""Tests for output_caps module."""

from __future__ import annotations

from src.application.services.output_caps import (
    CHARS_PER_TOKEN,
    cap_response,
    estimate_tokens,
    truncate_content,
)

TRUNCATION_MARKER = "\n[... truncated, use memory_get with id for full content]"


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_short_text(self) -> None:
        assert estimate_tokens("hello") == 1  # 5 // 4

    def test_exact_multiple(self) -> None:
        assert estimate_tokens("a" * 40) == 10

    def test_rounds_down(self) -> None:
        assert estimate_tokens("abc") == 0  # 3 // 4


# ---------------------------------------------------------------------------
# truncate_content
# ---------------------------------------------------------------------------

class TestTruncateContent:
    def test_small_content_unchanged(self) -> None:
        text = "short"
        result, truncated = truncate_content(text, 100)
        assert result == text
        assert truncated is False

    def test_large_content_truncated_with_marker(self) -> None:
        text = "x" * 400
        max_t = 50  # 200 chars budget — text is 400, so must truncate
        result, truncated = truncate_content(text, max_t)
        assert truncated is True
        assert result.endswith(TRUNCATION_MARKER)
        assert len(result) <= max_t * CHARS_PER_TOKEN

    def test_zero_budget_returns_marker_only(self) -> None:
        result, truncated = truncate_content("hello", 0)
        assert truncated is True
        # marker itself may not fit in 0-char budget, but we allow at least 0
        assert isinstance(result, str)

    def test_exact_fit_no_truncation(self) -> None:
        text = "a" * 40  # exactly 10 tokens
        result, truncated = truncate_content(text, 10)
        assert truncated is False
        assert result == text


# ---------------------------------------------------------------------------
# cap_response
# ---------------------------------------------------------------------------

def _obs(content: str, **extra: object) -> dict:
    """Helper to build a minimal observation dict."""
    d: dict = {"content": content}
    d.update(extra)
    return d


class TestCapResponse:
    def test_small_content_passes_through(self) -> None:
        obs = [_obs("hello")]
        result = cap_response(obs, max_tokens=100)
        assert len(result) == 1
        assert result[0]["content"] == "hello"
        assert "_truncated" not in result[0]

    def test_single_large_observation_truncated(self) -> None:
        content = "x" * 200
        obs = [_obs(content, id="abc")]
        # Full JSON: ~222 chars = 55 tokens. Overhead (capped): ~60 chars = 15 tokens.
        # Need budget > 15 (overhead) + 14 (marker) = 29 minimum.
        result = cap_response(obs, max_tokens=35)
        assert len(result) == 1
        assert result[0]["content"] != content
        assert result[0]["_truncated"] is True
        assert result[0]["_full_content_tokens"] >= estimate_tokens(content)

    def test_multiple_obs_fit_budget(self) -> None:
        obs = [_obs("short"), _obs("also short")]
        result = cap_response(obs, max_tokens=1000)
        assert len(result) == 2
        for r in result:
            assert "_truncated" not in r

    def test_stops_when_budget_exhausted(self) -> None:
        # First obs consumes all budget. Full JSON: {"content":"y"*40} = 55 chars.
        big = "y" * 40  # 10 content tokens, ~14 full JSON tokens (55 chars)
        obs = [_obs(big), _obs("extra")]
        result = cap_response(obs, max_tokens=14)
        assert len(result) == 1
        assert result[0]["content"] == big

    def test_truncation_marker_inside_budget(self) -> None:
        content = "z" * 200
        obs = [_obs(content, id="z1")]
        # Overhead (capped) ~15 tokens + marker ~14 tokens = 29 minimum.
        result = cap_response(obs, max_tokens=35)
        assert len(result) == 1
        assert result[0]["content"].endswith(TRUNCATION_MARKER)
        assert len(result[0]["content"]) <= 35 * CHARS_PER_TOKEN

    def test_empty_list(self) -> None:
        assert cap_response([]) == []

    def test_zero_max_tokens(self) -> None:
        assert cap_response([_obs("anything")], max_tokens=0) == []

    def test_negative_max_tokens(self) -> None:
        assert cap_response([_obs("anything")], max_tokens=-1) == []

    def test_no_truncated_flag_when_fits(self) -> None:
        obs = [_obs("fits")]
        result = cap_response(obs, max_tokens=100)
        assert "_truncated" not in result[0]
        assert "_full_content_tokens" not in result[0]
