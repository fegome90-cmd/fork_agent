from __future__ import annotations

import sqlite3

from src.infrastructure.persistence.repositories.observation_repository import ObservationRepository
from src.infrastructure.retrieval.v2 import EnhancedRetrievalSearchService, extract_concepts, plan_query


class TestConceptExtraction:
    def test_where_question_extracts_location_concepts(self) -> None:
        query = "where are fork sessions created"
        concepts = extract_concepts(query)

        assert concepts.question_type == "where"
        assert "fork" in concepts.concepts
        assert "session" in concepts.concepts
        assert "create" in concepts.concepts
        assert "endpoint" in concepts.concepts

    def test_when_question_extracts_policy_concepts(self) -> None:
        query = "when should observation be updated vs replaced"
        concepts = extract_concepts(query)

        assert concepts.question_type == "when"
        assert "observation" in concepts.concepts
        assert "update" in concepts.concepts
        assert "replace" in concepts.concepts
        assert "policy" in concepts.concepts


class TestQueryPlanning:
    def test_generates_multiple_fts5_variations(self) -> None:
        plan = plan_query("where are fork sessions created")

        assert len(plan.fts5_queries) >= 3
        assert any("session" in q for q in plan.fts5_queries)
        assert any("endpoint" in q for q in plan.fts5_queries)

    def test_expands_synonyms(self) -> None:
        plan = plan_query("how to create sessions")

        assert any("post" in q for q in plan.fts5_queries)


class TestEnhancedSearch:
    def test_finds_observation_with_natural_language(self, tmp_path: object) -> None:
        from pathlib import Path

        db_path = Path(str(tmp_path)) / "test_semantic.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE observations (id TEXT PRIMARY KEY, timestamp INTEGER, content TEXT, title TEXT, metadata TEXT, idempotency_key TEXT, topic_key TEXT, project TEXT, type TEXT, revision_count INTEGER DEFAULT 1, session_id TEXT)"
        )
        conn.execute(
            "CREATE VIRTUAL TABLE observations_fts USING fts5(content, title, topic_key, content=observations, tokenize='unicode61')"
        )
        conn.execute(
            "CREATE TRIGGER observations_ai AFTER INSERT ON observations BEGIN INSERT INTO observations_fts(rowid, content, title, topic_key) VALUES (new.rowid, new.content, new.title, new.topic_key); END"
        )
        conn.commit()

        import time

        test_data = [
            ("aaaa0001", "Fork sessions are created in /tmp/fork-live-sessions/ directory"),
            (
                "aaaa0002",
                "Archive old memory observations after pilot is complete or keep them live for reference",
            ),
            (
                "aaaa0003",
                "Observations should be updated when the topic evolves, replaced when the content is obsolete",
            ),
            (
                "aaaa0004",
                "Status field vs stability metric: stability wins when retrieving cached observations",
            ),
            (
                "aaaa0005",
                "Fallback contracts for tools ensure no silent failures in the orchestration pipeline",
            ),
        ]
        for short_id, content in test_data:
            full_id = f"{short_id}-0000-0000-0000-000000000000"
            conn.execute(
                "INSERT INTO observations (id, timestamp, content) VALUES (?, ?, ?)",
                (full_id, int(time.time() * 1000), content),
            )
        conn.commit()

        conn.row_factory = sqlite3.Row
        repository = ObservationRepository(conn)

        test_cases = [
            ("where are fork sessions created", "aaaa0001"),
            ("archive old memory after pilot or keep live", "aaaa0002"),
            ("when should an observation be updated vs replaced", "aaaa0003"),
            ("status vs stability what wins when retrieving", "aaaa0004"),
            ("fallback contracts for tools no silent failures", "aaaa0005"),
        ]

        for query, expected_prefix in test_cases:
            svc = EnhancedRetrievalSearchService(repository)
            results = svc.search(query, limit=5)
            ids = [result.id[:8] for result in results]
            assert expected_prefix in ids, (
                f"Query '{query}' should find {expected_prefix}, got {ids}"
            )

        conn.close()
