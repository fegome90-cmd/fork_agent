"""Query planning for semantic-bridge retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.retrieval.normalizer import normalize_query
from src.infrastructure.retrieval.sanitizer import sanitize_fts5
from src.infrastructure.retrieval.v2.concept_extractor import QueryConcept, extract_concepts


@dataclass(frozen=True)
class QueryPlan:
    original: str
    normalized: str
    concepts: QueryConcept
    fts5_queries: tuple[str, ...]


def _dedupe(values: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = sanitize_fts5(value)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return tuple(deduped)


def plan_query(query: str) -> QueryPlan:
    normalized = normalize_query(query)
    concepts = extract_concepts(query)

    concept_terms = sorted(concepts.concepts)
    synonym_terms = sorted({synonym for values in concepts.synonyms.values() for synonym in values})

    expanded_lines: list[str] = [
        normalized.sanitized,
        normalized.simplified,
        " ".join(concept_terms),
        " ".join(term for term in concept_terms + synonym_terms),
    ]

    # B4/B5 fix: add individual terms as separate FTS5 OR queries
    # so multi-word searches match observations containing any term
    for term in concept_terms:
        if len(term) > 2 and term not in (normalized.simplified, normalized.sanitized):
            expanded_lines.append(term)

    if concepts.question_type == "where":
        expanded_lines.extend(
            [
                f"{normalized.simplified} endpoint route api",
                f"{' '.join(concept_terms)} post endpoint",
            ]
        )
    if concepts.question_type == "when":
        expanded_lines.extend(
            [
                f"{normalized.simplified} policy rule lifecycle",
                f"{' '.join(concept_terms)} guidance decision",
            ]
        )
    if concepts.question_type == "how":
        expanded_lines.extend(
            [
                f"{normalized.simplified} procedure workflow",
                f"{' '.join(concept_terms)} create post",
            ]
        )

    return QueryPlan(
        original=query,
        normalized=normalized.simplified,
        concepts=concepts,
        fts5_queries=_dedupe(expanded_lines),
    )
