from __future__ import annotations

from src.infrastructure.retrieval.v2.semantic_bridge import expand_query_with_bridge


class TestOverlapRanking:
    def test_applies_top_n_bridges_regardless_of_overlap(self) -> None:
        query = "completely unrelated query xyz123"
        bridges = {
            "test-bridge": {
                "question_forms": ["unrelated question"],
                "concept_keywords": ["unrelated", "keywords"],
                "natural_phrasings": ["unrelated phrasing"],
            }
        }

        expansions = expand_query_with_bridge(
            query,
            bridges,
            top_n=3,
            min_overlap=0,
        )

        assert len(expansions) > 1

    def test_ranks_high_overlap_bridges_first(self) -> None:
        query = "gemini workers"
        bridges = {
            "high-overlap": {
                "question_forms": ["gemini faster than workers"],
                "concept_keywords": ["gemini", "workers"],
            },
            "low-overlap": {
                "question_forms": ["unrelated question"],
                "concept_keywords": ["unrelated"],
            },
        }

        expansions = expand_query_with_bridge(
            query,
            bridges,
            top_n=2,
        )

        assert expansions[1] == "gemini faster than workers"

    def test_limits_top_n_bridges(self) -> None:
        query = "test query"
        bridges = {
            f"bridge-{index}": {
                "question_forms": [f"question {index}"],
                "concept_keywords": [f"keyword{index}"],
            }
            for index in range(10)
        }

        expansions = expand_query_with_bridge(
            query,
            bridges,
            top_n=3,
        )

        assert (
            "question 0" in expansions or "question 1" in expansions or "question 2" in expansions
        )
        assert "question 9" not in expansions
        assert len(expansions) < 10
