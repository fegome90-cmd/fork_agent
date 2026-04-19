"""Retrieval hardening pipeline for observation search."""

from src.infrastructure.retrieval.expander import ExpandedQuery, expand_aliases
from src.infrastructure.retrieval.fallback import search_with_fallback
from src.infrastructure.retrieval.normalizer import NormalizedQuery, normalize_query
from src.infrastructure.retrieval.reranker import detect_intention, rerank_by_intention
from src.infrastructure.retrieval.sanitizer import sanitize_fts5
from src.infrastructure.retrieval.search import RetrievalSearchService
from src.infrastructure.retrieval.v2 import (
    EnhancedRetrievalSearchService,
    QueryConcept,
    QueryPlan,
    SearchResult,
    enhanced_search,
    expand_query_with_bridge,
    extract_concepts,
    get_bridge,
    plan_query,
)

__all__ = [
    "EnhancedRetrievalSearchService",
    "ExpandedQuery",
    "NormalizedQuery",
    "QueryConcept",
    "QueryPlan",
    "RetrievalSearchService",
    "SearchResult",
    "detect_intention",
    "enhanced_search",
    "expand_aliases",
    "expand_query_with_bridge",
    "extract_concepts",
    "get_bridge",
    "normalize_query",
    "plan_query",
    "rerank_by_intention",
    "sanitize_fts5",
    "search_with_fallback",
]
