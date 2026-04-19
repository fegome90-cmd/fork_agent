from __future__ import annotations

from src.domain.entities.observation import Observation
from src.infrastructure.retrieval.v2.enhanced_search import _build_search_blob, _score_observation


class TestRetrievalHintsSearchBlob:
    def test_build_search_blob_includes_content_and_metadata_hints(self) -> None:
        observation = Observation(
            id="test-123",
            timestamp=1,
            content="Original content without keywords",
            metadata={
                "retrieval_hints": {
                    "question_forms": ["test query form"],
                    "concept_keywords": ["test", "keyword"],
                    "natural_phrasings": ["natural test phrase"],
                }
            },
        )

        blob = _build_search_blob(observation)

        assert "original content without keywords" in blob
        assert "test query form" in blob
        assert "retrieval hints" in blob
        assert "test" in blob
        assert "keyword" in blob
        assert "natural test phrase" in blob

    def test_score_observation_uses_retrieval_hints(self) -> None:
        observation = Observation(
            id="test-456",
            timestamp=1,
            content="Procedure overview",
            metadata={
                "type": "procedure",
                "topic_key": "openclaw.procedures.branch-review",
                "retrieval_hints": {
                    "question_forms": ["how do i kick off branch review from cli"],
                    "concept_keywords": ["branch", "review", "cli", "kick", "off"],
                },
            },
        )

        with_hints = _score_observation(observation, "how do I kick off branch review from cli")
        without_hints = _score_observation(
            Observation(
                id="test-456",
                timestamp=1,
                content="Procedure overview",
                metadata={
                    "type": "procedure",
                    "topic_key": "openclaw.procedures.branch-review",
                },
            ),
            "how do I kick off branch review from cli",
        )

        assert with_hints > without_hints
