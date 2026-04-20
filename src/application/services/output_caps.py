"""Output caps and token estimation for MCP tool responses.

MCP tools (memory_search, memory_get, memory_list) return serialized
observations that can blow up the agent's context window when observations
are large or search returns many results. This module provides conservative
token estimation and response capping so callers stay within a budget.
"""

from __future__ import annotations

CHARS_PER_TOKEN: int = 4
DEFAULT_MAX_TOKENS: int = 8000
_TRUNCATION_MARKER: str = "\n[... truncated, use memory_get with id for full content]"


def estimate_tokens(text: str) -> int:
    """Conservative char-based token estimate (~4 chars per token)."""
    return len(text) // CHARS_PER_TOKEN


def truncate_content(content: str, max_tokens: int) -> tuple[str, bool]:
    """Truncate *content* to fit within *max_tokens*.

    When truncation is needed the marker is appended *inside* the budget.
    Returns (possibly_truncated_content, was_truncated).
    """
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(content) <= max_chars:
        return content, False

    marker_len = len(_TRUNCATION_MARKER)
    available = max_chars - marker_len
    if available > 0:
        return content[:available] + _TRUNCATION_MARKER, True
    # Marker doesn't fit — hard-truncate without it
    if max_chars > 0:
        return content[:max_chars], True
    # Zero budget
    return "", True


def cap_response(observations: list[dict], max_tokens: int = DEFAULT_MAX_TOKENS) -> list[dict]:
    """Fit serialized observation dicts within *max_tokens* budget.

    Each dict should have a ``"content"`` key.  Observations are processed
    in order.  If a single observation exceeds the remaining budget its
    content is truncated and annotated with ``_truncated`` and
    ``_full_content_tokens``.  Once the budget is exhausted no further
    observations are included.

    Budget accounts for the FULL serialized JSON (keys, metadata, syntax),
    not just the content field.
    """
    import json as _json

    max_tokens = int(max_tokens)  # B3: coerce float to int
    if max_tokens <= 0 or not observations:
        return []

    marker_len = len(_TRUNCATION_MARKER)
    budget_chars = max_tokens * CHARS_PER_TOKEN
    result: list[dict] = []
    remaining_chars = budget_chars

    for obs in observations:
        if remaining_chars <= 0:
            break

        # B1 fix: measure full JSON char size
        obs_json = _json.dumps(obs)
        obs_chars = len(obs_json)

        if obs_chars <= remaining_chars:
            # Entire observation fits within budget
            copy = obs.copy()
            copy.setdefault("content", "")
            result.append(copy)
            remaining_chars -= obs_chars
        else:
            # Over budget — try to truncate content to fit.
            content = obs.get("content", "")
            capped = obs.copy()
            capped.setdefault("content", "")
            capped["_truncated"] = True
            capped["_full_content_tokens"] = len(obs_json) // CHARS_PER_TOKEN

            # Measure overhead including the content key with empty value
            capped["content"] = ""
            overhead_chars = len(_json.dumps(capped))

            if overhead_chars >= remaining_chars:
                # Even with empty content, overhead exceeds budget — skip
                continue

            # Available chars for content value (inside JSON string)
            content_chars_budget = remaining_chars - overhead_chars
            # JSON escapes add overhead (newlines → \\n, etc). Use conservative budget.
            # Account for worst case: each char in content could be 2 chars in JSON.
            safe_content_chars = content_chars_budget - 2  # safety margin for JSON encoding

            if safe_content_chars <= 0:
                # No room for content at all
                capped["content"] = ""
                final = _json.dumps(capped)
                if len(final) <= remaining_chars:
                    result.append(capped)
                remaining_chars = 0
                break

            # Try content + marker
            if len(content) + marker_len <= safe_content_chars:
                capped["content"] = content + _TRUNCATION_MARKER
            elif safe_content_chars >= marker_len:
                capped["content"] = content[: safe_content_chars - marker_len] + _TRUNCATION_MARKER
            elif safe_content_chars > 0:
                capped["content"] = content[:safe_content_chars]
            else:
                capped["content"] = ""

            # Verify and shrink if needed
            final = _json.dumps(capped)
            if len(final) > remaining_chars:
                # JSON escaping made it too big — shrink by the excess
                excess = len(final) - remaining_chars
                current = capped["content"]
                shrink = max(excess + 4, len(current) // 4)  # shrink generously
                new_len = max(len(current) - shrink, 0)
                capped["content"] = current[:new_len]
                final = _json.dumps(capped)
                if len(final) > remaining_chars:
                    # Still too big — hard truncate
                    capped["content"] = content[: max(0, safe_content_chars - marker_len)]
                    final = _json.dumps(capped)
                    if len(final) > remaining_chars:
                        capped["content"] = ""
                        final = _json.dumps(capped)

            if len(_json.dumps(capped)) <= remaining_chars:
                result.append(capped)
            remaining_chars = 0
            break

    return result
