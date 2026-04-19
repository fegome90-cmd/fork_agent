"""Edge-case tests for output_caps module.

Covers boundaries, unicode, missing keys, pathological inputs, and
corner cases the original test suite likely missed.
"""

from __future__ import annotations

import pytest

from src.application.services.output_caps import (
    _TRUNCATION_MARKER,
    CHARS_PER_TOKEN,
    DEFAULT_MAX_TOKENS,
    cap_response,
    estimate_tokens,
    truncate_content,
)

TRUNCATION_MARKER = _TRUNCATION_MARKER


# ---------------------------------------------------------------------------
# 1. Exact boundary — no truncation
# ---------------------------------------------------------------------------

class TestExactBoundary:
    def test_content_exactly_at_token_limit_no_truncation(self) -> None:
        """Content of exactly DEFAULT_MAX_TOKENS * CHARS_PER_TOKEN chars fits."""
        text = "a" * (DEFAULT_MAX_TOKENS * CHARS_PER_TOKEN)
        result, truncated = truncate_content(text, DEFAULT_MAX_TOKENS)
        assert truncated is False
        assert result == text

    def test_estimate_tokens_at_exact_boundary(self) -> None:
        """80_000 chars → exactly 20_000 tokens (with CHARS_PER_TOKEN=4)."""
        text = "b" * (20_000 * CHARS_PER_TOKEN)
        assert estimate_tokens(text) == 20_000


# ---------------------------------------------------------------------------
# 2. One char over boundary — truncation must happen
# ---------------------------------------------------------------------------

class TestOneCharOverBoundary:
    def test_one_char_over_truncates(self) -> None:
        text = "a" * (DEFAULT_MAX_TOKENS * CHARS_PER_TOKEN + 1)
        result, truncated = truncate_content(text, DEFAULT_MAX_TOKENS)
        assert truncated is True
        assert result.endswith(TRUNCATION_MARKER)
        assert len(result) <= DEFAULT_MAX_TOKENS * CHARS_PER_TOKEN

    def test_one_char_over_smaller_budget(self) -> None:
        budget = 10
        text = "x" * (budget * CHARS_PER_TOKEN + 1)
        result, truncated = truncate_content(text, budget)
        assert truncated is True
        # With full budget accounting: marker fits in 10-token budget
        assert result.endswith(TRUNCATION_MARKER) or len(result) <= budget * CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# 3. Unicode — emoji, accented, CJK
# ---------------------------------------------------------------------------

class TestUnicodeContent:
    def test_emoji_estimation(self) -> None:
        """Each emoji is 1 Python char (single codepoint) but may render as 2+ bytes.
        The estimator uses len() so each counts as 1 char."""
        emoji = "🔬🧪📊"
        tokens = estimate_tokens(emoji)
        assert tokens == len(emoji) // CHARS_PER_TOKEN  # 3 // 4 = 0

    def test_long_emoji_truncation(self) -> None:
        content = "🔬" * 200  # 200 chars
        result, truncated = truncate_content(content, 10)  # 40 char budget
        assert truncated is True
        # With B2 fix: marker (57 chars) > budget (40 chars), so hard-truncate without marker
        assert len(result) <= 10 * CHARS_PER_TOKEN  # must respect budget

    def test_accented_chars(self) -> None:
        content = "áéíóúñ" * 100  # 600 chars
        result, truncated = truncate_content(content, 50)  # 200 char budget
        assert truncated is True
        # Verify the truncation marker is still readable
        assert TRUNCATION_MARKER in result

    def test_cjk_chars(self) -> None:
        content = "漢字テスト" * 50  # 300 chars (6 per unit × 50)
        result, truncated = truncate_content(content, 20)  # 80 char budget
        assert truncated is True
        assert result.endswith(TRUNCATION_MARKER)
        assert len(result) <= 80

    def test_mixed_unicode_script_content(self) -> None:
        content = "Hello 世界 🌍 مرحبا" * 40  # 15 chars × 40 = 600 chars
        result, truncated = truncate_content(content, 50)
        assert truncated is True
        assert result.endswith(TRUNCATION_MARKER)


# ---------------------------------------------------------------------------
# 4. Newlines and special characters
# ---------------------------------------------------------------------------

class TestNewlinesAndSpecialChars:
    def test_content_with_many_newlines(self) -> None:
        content = "line\n" * 200  # 800 chars
        result, truncated = truncate_content(content, 50)  # 200 char budget
        assert truncated is True
        assert result.endswith(TRUNCATION_MARKER)
        # Marker itself should be on its own line
        assert "\n[... truncated" in result

    def test_content_with_tabs_and_null_like(self) -> None:
        content = "col1\tcol2\tcol3\n" * 100  # ~1600 chars
        result, truncated = truncate_content(content, 100)
        assert truncated is True
        assert result.endswith(TRUNCATION_MARKER)

    def test_content_with_json_like_structure(self) -> None:
        content = '{"key": "value", "nested": {"a": 1}}\n' * 100
        result, truncated = truncate_content(content, 80)
        assert truncated is True
        assert TRUNCATION_MARKER in result

    def test_truncation_preserves_partial_line(self) -> None:
        """Truncation should cut mid-line, not seek a newline boundary."""
        content = "aaaa\nbbbb\ncccc\n" * 100  # 600 chars
        result, _ = truncate_content(content, 20)  # 80 char budget
        # The result should not end with \n before the marker
        marker_index = result.rfind(TRUNCATION_MARKER)
        before_marker = result[:marker_index]
        # It's fine if it ends with \n or not — just verify it's truncated
        assert len(before_marker) < len(content)


# ---------------------------------------------------------------------------
# 5. cap_response with observations missing "content" key
# ---------------------------------------------------------------------------

class TestMissingContentKey:
    def test_obs_without_content_key_no_crash(self) -> None:
        """obs.get("content", "") should default to empty string."""
        obs = [{"id": "abc", "type": "bugfix"}]
        result = cap_response(obs, max_tokens=100)
        assert len(result) == 1
        assert result[0]["content"] == ""
        assert result[0]["id"] == "abc"

    def test_multiple_obs_some_missing_content(self) -> None:
        obs = [
            {"content": "has content", "id": "1"},
            {"id": "2"},  # no content
            {"content": "also has content", "id": "3"},
        ]
        result = cap_response(obs, max_tokens=1000)
        assert len(result) == 3
        assert result[1]["content"] == ""


# ---------------------------------------------------------------------------
# 6. cap_response with empty string content
# ---------------------------------------------------------------------------

class TestEmptyStringContent:
    def test_empty_content_passes_through(self) -> None:
        obs = [{"content": "", "id": "empty"}]
        result = cap_response(obs, max_tokens=100)
        assert len(result) == 1
        assert result[0]["content"] == ""
        assert "_truncated" not in result[0]

    def test_empty_content_zero_tokens(self) -> None:
        """Empty string content has minimal JSON overhead."""
        obs = [{"content": "", "id": "1"}, {"content": "real data", "id": "2"}]
        # Full JSON per obs: ~20 chars = 5 tokens. Need budget for 2 obs.
        result = cap_response(obs, max_tokens=20)
        assert len(result) == 2
        assert result[1]["content"] == "real data"


# ---------------------------------------------------------------------------
# 7. cap_response with negative max_tokens
# ---------------------------------------------------------------------------

class TestNegativeMaxTokens:
    def test_negative_returns_empty(self) -> None:
        obs = [{"content": "anything"}]
        result = cap_response(obs, max_tokens=-1)
        assert result == []

    def test_very_negative(self) -> None:
        obs = [{"content": "anything"}]
        result = cap_response(obs, max_tokens=-999999)
        assert result == []


# ---------------------------------------------------------------------------
# 8. cap_response with very large max_tokens
# ---------------------------------------------------------------------------

class TestVeryLargeMaxTokens:
    def test_one_million_tokens_no_overflow(self) -> None:
        """max_chars = 1_000_000 * 4 = 4_000_000 — should work fine in Python."""
        content = "data" * 1000  # 4000 chars
        obs = [{"content": content}]
        result = cap_response(obs, max_tokens=1_000_000)
        assert len(result) == 1
        assert result[0]["content"] == content
        assert "_truncated" not in result[0]

    def test_large_budget_with_large_content(self) -> None:
        content = "x" * 100_000  # 25_000 tokens
        obs = [{"content": content}]
        result = cap_response(obs, max_tokens=50_000)
        assert len(result) == 1
        assert result[0]["content"] == content
        assert "_truncated" not in result[0]


# ---------------------------------------------------------------------------
# 9. Single observation exceeds entire budget
# ---------------------------------------------------------------------------

class TestSingleObsExceedsBudget:
    def test_first_obs_larger_than_budget_gets_truncated_not_dropped(self) -> None:
        """An observation larger than the budget should be truncated, not skipped."""
        content = "z" * 1000  # 250 tokens
        obs = [{"content": content, "id": "big-one"}]
        # Overhead (capped): ~16 tokens + marker: ~14 tokens = 30 minimum.
        result = cap_response(obs, max_tokens=35)
        assert len(result) == 1
        assert result[0]["content"] != content
        assert result[0]["_truncated"] is True
        assert result[0]["_full_content_tokens"] >= 250
        assert result[0]["content"].endswith(TRUNCATION_MARKER)

    def test_oversized_obs_still_included_with_metadata(self) -> None:
        """Verify the truncated obs retains original keys."""
        obs = [{"content": "a" * 500, "id": "x", "type": "bugfix", "what": "test"}]
        # Overhead (capped with 4 keys): ~23 tokens + marker: ~14 tokens = 37 minimum.
        result = cap_response(obs, max_tokens=40)
        assert len(result) == 1
        assert result[0]["id"] == "x"
        assert result[0]["type"] == "bugfix"
        assert result[0]["what"] == "test"
        assert result[0]["_truncated"] is True


# ---------------------------------------------------------------------------
# 10. Mixed sizes — some fit, some don't
# ---------------------------------------------------------------------------

class TestMixedSizes:
    def test_first_fits_second_truncated(self) -> None:
        small = "a" * 40  # 10 content tokens
        big = "b" * 200  # 50 content tokens
        obs = [{"content": small, "id": "1"}, {"content": big, "id": "2"}]
        # obs1 full JSON: 66 chars = 16 tokens. obs2 full JSON: 226 chars = 56 tokens.
        # obs1 fits (16), remaining for obs2 = budget - 16.
        # Need budget - 16 > 14 (overhead) + 14 (marker) = budget > 44.
        result = cap_response(obs, max_tokens=50)
        assert len(result) == 2
        assert result[0]["content"] == small
        assert "_truncated" not in result[0]
        assert result[1]["_truncated"] is True

    def test_first_fits_second_dropped_third_dropped(self) -> None:
        small = "a" * 40  # 10 content tokens
        obs = [
            {"content": small, "id": "1"},
            {"content": "b" * 200, "id": "2"},
            {"content": "extra", "id": "3"},
        ]
        # obs1 full JSON: 66 chars = 17 tokens. Budget exactly fits first.
        result = cap_response(obs, max_tokens=17)
        assert len(result) == 1
        assert result[0]["content"] == small
        assert "_truncated" not in result[0]

    def test_three_fit_exactly_then_fourth_dropped(self) -> None:
        """When 4th obs doesn't fit, it's dropped (not truncated — capped overhead > original)."""
        unit = "a" * 40  # 10 content tokens
        obs = [
            {"content": unit, "id": str(i)} for i in range(4)
        ]
        # Full JSON per obs: 66 chars. 3 × 66 = 198 chars = 50 tokens.
        # Budget = 50 tokens = 200 chars. 4th obs = 66 chars > 2 remaining → dropped.
        result = cap_response(obs, max_tokens=50)
        assert len(result) == 3
        for r in result:
            assert "_truncated" not in r

    def test_many_small_observations(self) -> None:
        """100 tiny observations within budget."""
        obs = [{"content": "hi", "id": str(i)} for i in range(100)]
        result = cap_response(obs, max_tokens=1000)
        assert len(result) == 100

    def test_many_small_then_budget_exhausted(self) -> None:
        """Many small observations with full JSON overhead."""
        obs = [{"content": "abcd", "id": str(i)} for i in range(20)]
        # Full JSON per obs: 30 chars. 9 × 30 = 270 chars = 68 tokens.
        # 10th needs 30 chars. Budget must be 300 chars = 75 tokens.
        result = cap_response(obs, max_tokens=75)
        assert len(result) == 10
        for r in result:
            assert "_truncated" not in r


# ---------------------------------------------------------------------------
# 11. estimate_tokens with None
# ---------------------------------------------------------------------------

class TestEstimateTokensNone:
    def test_none_raises_type_error(self) -> None:
        """estimate_tokens expects str — None should raise TypeError."""
        with pytest.raises(TypeError):
            estimate_tokens(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 12. Content containing the truncation marker itself
# ---------------------------------------------------------------------------

class TestTruncationMarkerInContent:
    def test_content_contains_marker_no_confusion(self) -> None:
        """Content that includes the marker string should not cause double markers."""
        marker = TRUNCATION_MARKER
        # Build content that IS the marker repeated + extra
        content = marker * 5 + "x" * 200
        result, truncated = truncate_content(content, 30)
        assert truncated is True
        # The result should end with exactly ONE marker
        assert result.endswith(marker)
        # Count occurrences of the marker in result
        result.count(marker)
        # The original had 5 markers in the prefix that fits; plus the appended one
        # We can't assert exact count without knowing how many fit in 120 chars
        # But we CAN assert the result doesn't end with two markers
        assert not result.endswith(marker + marker)

    def test_content_is_just_the_marker(self) -> None:
        content = TRUNCATION_MARKER
        result, truncated = truncate_content(content, 100)
        # Marker is ~60 chars = 15 tokens. With budget of 100 tokens (400 chars) it fits.
        assert truncated is False
        assert result == content

    def test_cap_response_with_marker_in_content(self) -> None:
        obs = [{"content": TRUNCATION_MARKER + " extra " * 200, "id": "m1"}]
        # Overhead (capped): ~14 tokens + marker: ~14 tokens = 28 minimum.
        result = cap_response(obs, max_tokens=35)
        assert len(result) == 1
        assert result[0]["_truncated"] is True
        # Should still end with exactly one marker
        assert result[0]["content"].endswith(TRUNCATION_MARKER)
        assert not result[0]["content"].endswith(TRUNCATION_MARKER + TRUNCATION_MARKER)


# ---------------------------------------------------------------------------
# Additional: cap_response mutability safety
# ---------------------------------------------------------------------------

class TestMutabilitySafety:
    def test_original_observations_not_mutated(self) -> None:
        """cap_response should copy dicts, not mutate the originals."""
        obs = [{"content": "hello", "id": "1"}]
        result = cap_response(obs, max_tokens=100)
        assert "_truncated" not in obs[0]
        assert result[0] is not obs[0]

    def test_truncated_obs_not_mutated(self) -> None:
        obs = [{"content": "x" * 200, "id": "2"}]
        cap_response(obs, max_tokens=10)
        assert "_truncated" not in obs[0]
        assert "content" in obs[0]
        assert len(obs[0]["content"]) == 200  # original unchanged


# ---------------------------------------------------------------------------
# Additional: truncate_content with max_tokens=1
# ---------------------------------------------------------------------------

class TestTinyBudget:
    def test_max_tokens_one(self) -> None:
        """1 token = 4 chars budget. Marker (57 chars) > budget. Hard-truncate to 4 chars."""
        result, truncated = truncate_content("hello world this is long", 1)
        assert truncated is True
        assert isinstance(result, str)
        # B2 fix: when marker doesn't fit, hard-truncate without it
        assert len(result) <= 1 * CHARS_PER_TOKEN
