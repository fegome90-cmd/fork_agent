"""Semantic concept extraction for natural-language retrieval queries."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.retrieval.normalizer import normalize_query

_QUESTION_HINTS: dict[str, set[str]] = {
    "where": {"endpoint", "route", "path", "location", "reference"},
    "when": {"policy", "rule", "lifecycle", "precedence", "timing"},
    "what": {"definition", "concept", "reference"},
    "how": {"procedure", "workflow", "steps", "create"},
    "should": {"policy", "rule", "decision"},
}

_CANONICAL_MAP = {
    "sessions": "session",
    "created": "create",
    "creating": "create",
    "creation": "create",
    "updated": "update",
    "updating": "update",
    "replaced": "replace",
    "replacing": "replace",
    "supersede": "replace",
    "superseded": "replace",
    "retrieving": "retrieve",
    "retrieval": "retrieve",
    "failures": "failure",
    "contracts": "contract",
    "tools": "tool",
    "observations": "observation",
}

_SYNONYMS: dict[str, list[str]] = {
    "create": ["created", "creation", "post", "new"],
    "session": ["sessions", "agent", "agents"],
    "endpoint": ["route", "api", "path"],
    "route": ["endpoint", "api", "path"],
    "archive": ["historical", "keep", "retain"],
    "memory": ["engram", "diary", "history"],
    "pilot": ["validation", "trial"],
    "update": ["updated", "refine", "refinement"],
    "replace": ["replaced", "supersede", "superseded"],
    "observation": ["observations", "memory"],
    "status": ["state", "active"],
    "stability": ["stable", "unstable", "precedence"],
    "retrieve": ["retrieval", "search", "recover"],
    "fallback": ["alternative", "degrade"],
    "contract": ["contracts", "policy", "explicit"],
    "failure": ["failures", "silent"],
    "tool": ["tools", "integration"],
    "policy": ["rule", "guidance"],
}


@dataclass(frozen=True)
class QueryConcept:
    question_type: str
    concepts: frozenset[str]
    synonyms: dict[str, tuple[str, ...]]


def _detect_question_type(query: str) -> str:
    tokens = query.casefold().split()
    for candidate in ("where", "when", "what", "how", "should"):
        if candidate in tokens:
            return candidate
    return "general"


def _canonicalize(token: str) -> str:
    return _CANONICAL_MAP.get(token, token)


def extract_concepts(query: str) -> QueryConcept:
    normalized = normalize_query(query)
    question_type = _detect_question_type(query)

    concepts: set[str] = set()
    for token in normalized.keywords:
        canonical = _canonicalize(token)
        concepts.add(canonical)

    for inferred in _QUESTION_HINTS.get(question_type, set()):
        concepts.add(inferred)

    if "replace" in concepts:
        concepts.add("lifecycle")
    if "archive" in concepts:
        concepts.add("historical")
    if "status" in concepts or "stability" in concepts:
        concepts.add("precedence")
    if "fallback" in concepts:
        concepts.add("explicit")

    synonyms: dict[str, tuple[str, ...]] = {}
    for concept in sorted(concepts):
        related = _SYNONYMS.get(concept, [])
        if related:
            synonyms[concept] = tuple(related)

    return QueryConcept(
        question_type=question_type,
        concepts=frozenset(concepts),
        synonyms=synonyms,
    )
