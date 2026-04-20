"""Explicit semantic bridge data for known retrieval gaps."""

from __future__ import annotations

from typing import Any

from src.infrastructure.retrieval.sanitizer import sanitize_fts5
from src.infrastructure.retrieval.v2.bridge_logger import BridgeDecision, log_bridge_decision

RETRIEVAL_BRIDGES: dict[str, dict[str, list[str]]] = {
    "ebea61a6-00a2-4efe-8a50-f2b4bfba25bd": {
        "question_forms": [
            "where are fork sessions created",
            "how to create fork sessions",
            "fork session creation endpoint",
        ],
        "concept_keywords": [
            "fork",
            "session",
            "sessions",
            "create",
            "created",
            "creation",
            "endpoint",
            "POST",
            "route",
            "API",
            "agents",
            "localhost",
        ],
        "natural_phrasings": [
            "fork sessions endpoint",
            "sessions created via API",
            "POST endpoint for sessions",
        ],
    },
    "8cf4838a-1458-4483-bb2a-0bf4113a143a": {
        "question_forms": [
            "archive old memory after pilot",
            "what to do with memory after pilot",
            "keep or archive memory files",
        ],
        "concept_keywords": [
            "archive",
            "memory",
            "pilot",
            "keep",
            "delete",
            "historical",
            "raw",
            "diary",
            "migrate",
            "lot",
            "validation",
        ],
        "natural_phrasings": [
            "archive policy memory",
            "memory files after pilot",
            "keep memory as historical",
        ],
    },
    "77e8384a-793d-4906-8fd1-a1e2039cbaf5": {
        "question_forms": [
            "when should observation be updated vs replaced",
            "update or supersede observation",
            "lifecycle update replace difference",
        ],
        "concept_keywords": [
            "observation",
            "update",
            "replace",
            "supersede",
            "lifecycle",
            "refine",
            "change",
            "version",
            "topic",
            "same",
            "different",
        ],
        "natural_phrasings": [
            "lifecycle update vs supersede",
            "when to update or replace",
            "observation lifecycle policy",
        ],
    },
    "94e7ac8e-9272-4981-b747-df092703d43c": {
        "question_forms": [
            "status vs stability what wins",
            "status stability precedence",
            "which wins status or stability",
        ],
        "concept_keywords": [
            "status",
            "stability",
            "wins",
            "precedence",
            "retrieve",
            "retrieval",
            "active",
            "stable",
            "unstable",
            "priority",
            "degrade",
        ],
        "natural_phrasings": [
            "status vs stability retrieval",
            "stability wins over status",
            "precedence stability status",
        ],
    },
    "6c94a28c-2565-4923-8d15-628eff14ac53": {
        "question_forms": [
            "fallback contracts for tools no silent failures",
            "explicit fallback contracts",
            "tool fallback without silent failure",
        ],
        "concept_keywords": [
            "fallback",
            "contract",
            "explicit",
            "silent",
            "failure",
            "tool",
            "integration",
            "trigger",
            "alternative",
            "behavior",
            "document",
        ],
        "natural_phrasings": [
            "fallback contracts explicit",
            "no silent failures",
            "explicit fallback behavior",
        ],
    },
    "2547eb47-4824-42bf-82a5-a2c397a84b08": {
        "question_forms": [
            "how do I kick off branch review from cli",
            "start branch review",
            "run branch review from command line",
        ],
        "concept_keywords": [
            "branch",
            "review",
            "workflow",
            "cli",
            "command",
            "start",
            "kick",
            "off",
            "init",
            "procedure",
        ],
        "natural_phrasings": [
            "branch review workflow",
            "kick off branch review",
            "start review from cli",
        ],
    },
    "f8f2c14d-3e9c-4e3a-b119-4cf8e1c6fc27": {
        "question_forms": [
            "gemini faster than claude workers",
            "is gemini faster than claude workers",
            "gemini versus claude workers speed",
        ],
        "concept_keywords": [
            "performance",
            "speed",
            "rate",
            "faster",
            "workers",
            "gemini",
            "claude",
            "rate",
            "limiting",
            "direct",
            "cli",
        ],
        "natural_phrasings": [
            "gemini direct cli faster",
            "claude workers rate limiting",
            "performance gemini vs claude workers",
        ],
    },
    "cd34a8c8-8ac4-4330-80de-9bb1c0cf3287": {
        "question_forms": [
            "why paths get hyphens instead of underscores",
            "why underscores replaced with hyphens",
        ],
        "concept_keywords": [
            "underscores",
            "hyphens",
            "paths",
            "convert",
            "replace",
            "bug",
            "claude-session-driver",
        ],
        "natural_phrasings": [
            "hyphens instead of underscores",
            "path conversion bug",
        ],
    },
    "e29b1278-9de4-4f75-b19e-4a5878a56b0c": {
        "question_forms": [
            "should official guidance beat memory notes",
            "official guidance vs memory notes",
        ],
        "concept_keywords": [
            "official",
            "guidance",
            "memory",
            "notes",
            "precedence",
            "beat",
            "priority",
            "intent",
            "based",
        ],
        "natural_phrasings": [
            "official guidance precedence",
            "memory notes priority",
        ],
    },
    "984f0285-593e-44e5-ac09-c97955b2173a": {
        "question_forms": [
            "retrieval backend configured for openclaw",
            "what retrieval backend is configured for openclaw",
            "openclaw retrieval backend configured",
        ],
        "concept_keywords": [
            "sqlite",
            "fts5",
            "stack",
            "backend",
            "configured",
            "openclaw",
            "retrieval",
            "memory",
        ],
        "natural_phrasings": [
            "openclaw retrieval stack",
            "sqlite fts5 backend",
            "configured retrieval backend",
        ],
    },
}


def get_bridge(observation_id: str) -> dict[str, list[str]] | None:
    return RETRIEVAL_BRIDGES.get(observation_id)


def _overlap_score(query_terms: set[str], bridge: dict[str, list[str]]) -> int:
    bridge_terms: set[str] = set()
    for values in bridge.values():
        for value in values:
            bridge_terms.update(sanitize_fts5(value).split())
    return len(query_terms & bridge_terms)


def expand_query_with_bridge(
    query: str,
    bridges: dict[str, dict[str, Any]],
    top_n: int = 3,
    min_overlap: int = 0,
    penalty_weight: float = 0.5,
) -> list[str]:
    del penalty_weight

    query_terms = set(sanitize_fts5(query).split())
    expansions: list[str] = [sanitize_fts5(query)]
    zero_overlap_limit = min(top_n, 2)
    zero_overlap_applied = 0

    bridge_scores: list[tuple[str, dict[str, Any], int]] = [
        (bridge_id, bridge, _overlap_score(query_terms, bridge))
        for bridge_id, bridge in bridges.items()
    ]
    ranked = sorted(
        bridge_scores,
        key=lambda item: item[2],
        reverse=True,
    )

    applied_bridges = 0
    for bridge_id, bridge, overlap in ranked:
        if applied_bridges >= top_n:
            break
        if overlap < min_overlap:
            log_bridge_decision(
                BridgeDecision(
                    query=query,
                    bridge_id=bridge_id,
                    overlap_score=overlap,
                    applied=False,
                    reason="below_min_overlap",
                    expansions_added=0,
                )
            )
            continue
        if overlap == 0 and zero_overlap_applied >= zero_overlap_limit:
            log_bridge_decision(
                BridgeDecision(
                    query=query,
                    bridge_id=bridge_id,
                    overlap_score=overlap,
                    applied=False,
                    reason="zero_overlap_limit_reached",
                    expansions_added=0,
                )
            )
            continue

        before_count = len(expansions)
        for key in ("question_forms", "natural_phrasings"):
            for value in bridge.get(key, []):
                sanitized = sanitize_fts5(value)
                if sanitized and sanitized not in expansions:
                    expansions.append(sanitized)
        concept_keywords = sanitize_fts5(" ".join(bridge.get("concept_keywords", [])))
        if concept_keywords and concept_keywords not in expansions:
            expansions.append(concept_keywords)

        applied_bridges += 1
        if overlap == 0:
            zero_overlap_applied += 1

        log_bridge_decision(
            BridgeDecision(
                query=query,
                bridge_id=bridge_id,
                overlap_score=overlap,
                applied=True,
                reason="ranked_top_n",
                expansions_added=len(expansions) - before_count,
            )
        )
    return expansions
