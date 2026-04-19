"""Fallback retrieval pipeline with query variants."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.observation import Observation
from src.infrastructure.retrieval.expander import expand_aliases
from src.infrastructure.retrieval.normalizer import normalize_query
from src.infrastructure.retrieval.reranker import detect_intention
from src.infrastructure.retrieval.sanitizer import sanitize_fts5


class SearchRepository(Protocol):
    def search(self, query: str, limit: int | None = None) -> list[Observation]: ...


_INTENT_FALLBACK_SUFFIX = {
    "operational": "procedure decision pattern lifecycle",
    "historical": "memory discovery learning",
    "official": "docs guide official reference policy",
    "lookup": "reference config workaround",
    "general": "",
}


def dedupe_observations(results: list[Observation]) -> list[Observation]:
    deduped: list[Observation] = []
    seen: set[str] = set()
    for observation in results:
        if observation.id in seen:
            continue
        seen.add(observation.id)
        deduped.append(observation)
    return deduped


def _candidate_queries(query: str) -> list[str]:
    normalized = normalize_query(query)
    expanded = expand_aliases(normalized)
    intention = detect_intention(query)

    variants: list[str] = []
    for candidate in [
        sanitize_fts5(query),
        normalized.simplified,
        *expanded.variants,
    ]:
        if candidate and candidate not in variants:
            variants.append(candidate)

    suffix = _INTENT_FALLBACK_SUFFIX[intention]
    if suffix:
        for base in [sanitize_fts5(query), normalized.simplified]:
            if not base:
                continue
            candidate = f"{base} {suffix}".strip()
            if candidate not in variants:
                variants.append(candidate)
    return variants


def search_with_fallback(
    repository: SearchRepository,
    query: str,
    limit: int,
) -> list[Observation]:
    collected: list[Observation] = []
    for candidate in _candidate_queries(query):
        results = repository.search(candidate, limit=limit)
        if results:
            collected.extend(results)
        deduped = dedupe_observations(collected)
        if len(deduped) >= limit:
            return deduped[:limit]
    return dedupe_observations(collected)[:limit]
