"""Natural-language query normalization for retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.retrieval.sanitizer import sanitize_fts5, tokenize_for_fts

STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "do",
    "does",
    "how",
    "why",
    "where",
    "when",
    "what",
    "should",
    "than",
    "from",
    "for",
    "to",
    "of",
    "in",
    "on",
    "be",
    "i",
    "we",
    "you",
    "it",
    "or",
    "and",
    "after",
    "before",
    "with",
    "without",
    "el",
    "la",
    "los",
    "las",
    "de",
    "del",
    "que",
    "como",
    "por",
    "para",
    "cuando",
    "donde",
    "si",
    "un",
    "una",
    "y",
    "o",
    "instead",
}

_DOMAIN_TERMS = {
    "fts5",
    "sqlite",
    "openclaw",
    "status",
    "stability",
    "docs",
    "memory",
    "api",
    "cli",
    "pi",
    "gemini",
    "claude",
}


@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    sanitized: str
    keywords: tuple[str, ...]
    simplified: str


def singularize_token(token: str) -> str:
    if token in _DOMAIN_TERMS or len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("ses") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in STOPWORDS:
            continue
        singular = singularize_token(token)
        candidate = singular if singular not in STOPWORDS else token
        if candidate in STOPWORDS:
            continue
        if candidate not in seen:
            seen.add(candidate)
            normalized.append(candidate)
    return normalized


def normalize_query(query: str) -> NormalizedQuery:
    sanitized = sanitize_fts5(query)
    tokens = tokenize_for_fts(query)
    keywords = tuple(normalize_tokens(tokens))
    simplified = " ".join(keywords)
    return NormalizedQuery(
        original=query,
        sanitized=sanitized,
        keywords=keywords,
        simplified=simplified,
    )
