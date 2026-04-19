"""Enhanced retrieval search with semantic bridging."""

from __future__ import annotations

from dataclasses import dataclass
import json

from src.domain.entities.observation import Observation
from src.domain.ports.observation_repository import ObservationRepository
from src.infrastructure.retrieval.reranker import detect_intention
from src.infrastructure.retrieval.sanitizer import sanitize_fts5
from src.infrastructure.retrieval.v2.bridge_logger import log_query_expansions
from src.infrastructure.retrieval.v2.query_planner import plan_query
from src.infrastructure.retrieval.v2.semantic_bridge import RETRIEVAL_BRIDGES, expand_query_with_bridge


@dataclass(frozen=True)
class SearchResult:
    id: str
    content: str
    score: float
    source: str


def _bridge_blob(metadata: dict[str, object] | None, observation_id: str) -> str:
    bridge = RETRIEVAL_BRIDGES.get(observation_id, {})
    metadata_hints = {}
    if metadata:
        raw_hints = metadata.get("retrieval_hints")
        if isinstance(raw_hints, dict):
            metadata_hints = raw_hints

    fields: list[str] = []
    for source in (bridge, metadata_hints):
        for key in ("question_forms", "concept_keywords", "natural_phrasings"):
            value = source.get(key, []) if isinstance(source, dict) else []
            if isinstance(value, list):
                fields.extend(str(item) for item in value)
    return sanitize_fts5(" ".join(fields))


def _build_search_blob(observation: Observation) -> str:
    """Build a searchable blob from content plus retrieval hints."""
    metadata_blob = ""
    if observation.metadata:
        try:
            metadata_blob = json.dumps(observation.metadata, ensure_ascii=False)
        except TypeError:
            metadata_blob = ""

    parts = [
        observation.content,
        metadata_blob,
        _bridge_blob(observation.metadata, observation.id),
    ]
    return sanitize_fts5(" ".join(part for part in parts if part))


def _question_type_boost(question_type: str, observation: Observation) -> float:
    obs_type = str((observation.metadata or {}).get("type", "")).casefold()
    topic_key = str((observation.metadata or {}).get("topic_key", "")).casefold()
    if question_type == "where" and (obs_type == "reference" or "endpoint" in topic_key):
        return 2.0
    if question_type == "when" and (obs_type in {"policy", "lifecycle"} or "lifecycle" in topic_key):
        return 2.0
    if question_type in {"what", "should", "general"} and any(
        marker in topic_key for marker in {"policy", "precedence", "fallback", "archive"}
    ):
        return 1.5
    return 0.0


def _score_observation(observation: Observation, query: str) -> float:
    plan = plan_query(query)
    query_terms = set(sanitize_fts5(query).split())
    content_terms = set(sanitize_fts5(observation.content).split())
    bridge_terms = set(_bridge_blob(observation.metadata, observation.id).split())
    search_blob_terms = set(_build_search_blob(observation).split())

    content_overlap = len(query_terms & content_terms)
    bridge_overlap = len(query_terms & bridge_terms)
    search_overlap = len(query_terms & search_blob_terms)
    concept_overlap = len(set(plan.concepts.concepts) & search_blob_terms)
    synonym_overlap = sum(
        1
        for values in plan.concepts.synonyms.values()
        if set(values) & search_blob_terms
    )

    density_denominator = max(len(search_blob_terms), 1)
    keyword_density = (search_overlap + bridge_overlap + concept_overlap) / density_denominator

    score = float(content_overlap)
    score += bridge_overlap * 3.0
    score += (search_overlap - content_overlap) * 1.5
    score += concept_overlap * 2.0
    score += synonym_overlap * 1.5
    score += keyword_density * 5.0
    score += _question_type_boost(plan.concepts.question_type, observation)

    metadata = observation.metadata or {}
    if str(metadata.get("status", "")).casefold() in {"active", "current"}:
        score += 1.0
    if str(metadata.get("stability", "")).casefold() in {"stable", "canonical"}:
        score += 1.0
    return score


def _dedupe_results(observations: list[tuple[Observation, str]]) -> list[tuple[Observation, str]]:
    deduped: list[tuple[Observation, str]] = []
    seen: set[str] = set()
    for observation, source in observations:
        if observation.id in seen:
            continue
        seen.add(observation.id)
        deduped.append((observation, source))
    return deduped


class EnhancedRetrievalSearchService:
    __slots__ = ("_repository",)

    def __init__(self, repository: ObservationRepository) -> None:
        self._repository = repository

    def search(
        self,
        query: str,
        limit: int | None = None,
        project: str | None = None,
        type: str | None = None,
        session_id: str | None = None,
    ) -> list[Observation]:
        effective_limit = limit or 5
        candidate_limit = max(effective_limit, min(effective_limit * 4, 20))
        plan = plan_query(query)
        candidates: list[str] = list(plan.fts5_queries)
        expansions = expand_query_with_bridge(query, RETRIEVAL_BRIDGES)
        log_query_expansions(query, expansions)
        for expanded in expansions:
            if expanded not in candidates:
                candidates.append(expanded)

        collected: list[tuple[Observation, str]] = []
        for index, candidate in enumerate(candidates):
            results = self._repository.search(
                candidate, limit=candidate_limit, project=project, type_=type, session_id=session_id
            )
            if not results:
                continue
            source = "bridge" if index >= len(plan.fts5_queries) else "expanded"
            for observation in results:
                collected.append((observation, source))

        deduped = _dedupe_results(collected)
        ranked = sorted(
            deduped,
            key=lambda item: (_score_observation(item[0], query), item[0].timestamp),
            reverse=True,
        )
        return [observation for observation, _source in ranked[:effective_limit]]


def enhanced_search(
    repository: ObservationRepository,
    query: str,
    limit: int = 5,
) -> list[SearchResult]:
    plan = plan_query(query)
    candidates: list[str] = list(plan.fts5_queries)
    expansions = expand_query_with_bridge(query, RETRIEVAL_BRIDGES)
    log_query_expansions(query, expansions)
    for expanded in expansions:
        if expanded not in candidates:
            candidates.append(expanded)

    collected: list[tuple[Observation, str]] = []
    for index, candidate in enumerate(candidates):
        results = repository.search(candidate, limit=limit * 4)
        if not results:
            continue
        source = "bridge" if index >= len(plan.fts5_queries) else "expanded"
        for observation in results:
            collected.append((observation, source))

    ranked = sorted(
        _dedupe_results(collected),
        key=lambda item: (_score_observation(item[0], query), item[0].timestamp),
        reverse=True,
    )
    return [
        SearchResult(
            id=observation.id,
            content=observation.content,
            score=_score_observation(observation, query),
            source=source,
        )
        for observation, source in ranked[:limit]
    ]
