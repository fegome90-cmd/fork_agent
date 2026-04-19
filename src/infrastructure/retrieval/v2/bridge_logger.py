from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BridgeDecision:
    query: str
    bridge_id: str
    overlap_score: int
    applied: bool
    reason: str
    expansions_added: int


def log_bridge_decision(decision: BridgeDecision) -> None:
    logger.debug(
        "Bridge decision: query='%s' bridge=%s overlap=%d applied=%s reason='%s' expansions=%d",
        decision.query[:50],
        decision.bridge_id[:8],
        decision.overlap_score,
        decision.applied,
        decision.reason,
        decision.expansions_added,
    )


def log_query_expansions(query: str, expansions: list[str]) -> None:
    logger.info(
        "Query expansions: query='%s' total=%d expansions=%s",
        query[:50],
        len(expansions),
        [expansion[:30] for expansion in expansions[:5]],
    )
