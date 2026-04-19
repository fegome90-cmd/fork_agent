"""Heuristic reranking based on query intention and observation metadata."""

from __future__ import annotations

from collections.abc import Iterable

from src.domain.entities.observation import Observation
from src.infrastructure.retrieval.sanitizer import sanitize_fts5

_INTENT_KEYWORDS = {
    "operational": {"how", "kick", "start", "launch", "procedure", "cli", "command"},
    "historical": {"why", "when", "history", "discovery", "happened"},
    "official": {"official", "guidance", "docs", "policy", "contract", "reference"},
    "lookup": {"where", "configured", "endpoint", "path", "reference"},
}

_INTENT_TYPE_BOOSTS = {
    "operational": {"procedure": 3.0, "decision": 2.5, "pattern": 2.0, "policy": 1.5, "lifecycle": 1.5},
    "historical": {"discovery": 3.0, "learning": 2.5, "memory": 2.0},
    "official": {"reference": 3.0, "policy": 2.5, "decision": 2.0},
    "lookup": {"reference": 3.0, "config": 2.5, "workaround": 2.0},
    "general": {},
}


def detect_intention(query: str) -> str:
    lowered = sanitize_fts5(query)
    tokens = set(lowered.split())
    for intention, keywords in _INTENT_KEYWORDS.items():
        if tokens & keywords:
            return intention
    return "general"


def _metadata_terms(observation: Observation) -> tuple[str, str, str]:
    metadata = observation.metadata or {}
    return (
        str(metadata.get("type", "")).casefold(),
        str(metadata.get("status", "")).casefold(),
        str(metadata.get("stability", "")).casefold(),
    )


def score_result(obs: Observation, intention: str, query: str) -> float:
    content = sanitize_fts5(obs.content)
    query_terms = sanitize_fts5(query).split()
    overlap = sum(1.0 for term in query_terms if term in content)

    obs_type, status, stability = _metadata_terms(obs)
    score = overlap
    score += _INTENT_TYPE_BOOSTS.get(intention, {}).get(obs_type, 0.0)

    origin_hint = str((obs.metadata or {}).get("origin_hint", "")).casefold()
    if intention == "historical" and "memory" in origin_hint:
        score += 1.5
    if intention == "official" and "docs" in origin_hint:
        score += 1.5

    if status in {"active", "current"}:
        score += 1.5
    if stability in {"stable", "canonical"}:
        score += 1.5
    return score


def rerank_by_intention(
    results: Iterable[Observation],
    intention: str,
    query: str,
) -> list[Observation]:
    return sorted(
        list(results),
        key=lambda obs: (score_result(obs, intention, query), obs.timestamp),
        reverse=True,
    )
