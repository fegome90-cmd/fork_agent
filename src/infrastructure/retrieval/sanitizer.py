"""FTS5 query sanitization helpers."""

from __future__ import annotations

import re
import unicodedata

_RESERVED_WORDS = {"AND", "OR", "NOT", "NEAR", "COLUMN"}
_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]+", re.UNICODE)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def tokenize_for_fts(query: str) -> list[str]:
    if not query or not query.strip():
        return []

    normalized = _strip_accents(query.casefold())
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = _PUNCTUATION_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized).strip()
    if not normalized:
        return []

    return [
        token for token in normalized.split(" ") if token and token.upper() not in _RESERVED_WORDS
    ]


def build_safe_match_query(tokens: list[str]) -> str:
    return " ".join(token for token in tokens if token)


def sanitize_fts5(query: str) -> str:
    return build_safe_match_query(tokenize_for_fts(query))
