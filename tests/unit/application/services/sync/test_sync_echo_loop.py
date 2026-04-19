"""Tests for echo loop prevention during import.

Bug 1: Import operations must not create ghost mutations that get re-exported.
Bug 2: upsert_topic_key must record mutations (was dead code after return).
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from src.domain.entities.observation import Observation


def _make_obs(
    obs_id: str = "test-1",
    content: str = "hello",
    topic_key: str | None = None,
    project: str | None = None,
) -> Observation:
    return Observation(
        id=obs_id,
        timestamp=1000,
        content=content,
        metadata=None,
        topic_key=topic_key,
        project=project,
    )


def _make_test_db() -> tuple[sqlite3.Connection, Path]:
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    conn = sqlite3.connect(str(tmp))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE observations (
            id TEXT PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            idempotency_key TEXT UNIQUE,
            topic_key TEXT,
            project TEXT,
            type TEXT,
            revision_count INTEGER DEFAULT 1,
            session_id TEXT,
            title TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
            content, metadata, title, topic_key, content=observations, content_rowid=rowid
        )
    """)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sync_chunks (
            chunk_id TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'local',
            imported_at INTEGER NOT NULL DEFAULT 0,
            observation_count INTEGER NOT NULL DEFAULT 0,
            checksum TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sync_mutations (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            op TEXT NOT NULL CHECK(op IN ('insert','update','delete')),
            payload TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'local',
            project TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sync_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_export_at INTEGER,
            last_import_at INTEGER,
            last_export_seq INTEGER DEFAULT 0,
            mutation_count INTEGER DEFAULT 0
        );
        INSERT OR IGNORE INTO sync_status (id) VALUES (1);
    """)
    return conn, tmp


def _wire_repos(db_path: Path):
    from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
    from src.infrastructure.persistence.repositories.observation_repository import (
        ObservationRepository,
    )
    from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

    db_conn = DatabaseConnection(config=DatabaseConfig(db_path=db_path))
    sync_repo = SyncRepositoryImpl(connection=db_conn)
    obs_repo = ObservationRepository(connection=db_conn, sync_repo=sync_repo)
    return obs_repo, sync_repo


# ---------------------------------------------------------------------------
# Bug 2: upsert_topic_key must record mutations
# ---------------------------------------------------------------------------

class TestUpsertTopicKeyMutation:
    """Bug 2: _record_mutation was dead code (after return) in upsert_topic_key."""

    def test_upsert_topic_key_records_update_mutation(self) -> None:
        """upsert_topic_key must record an 'update' mutation."""
        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)

        # Create observation with topic_key
        obs_repo.create(_make_obs("tk-1", "v1", topic_key="bug2-test", project="testproj"))

        # Upsert (update content via topic_key)
        updated = Observation(
            id="tk-1",
            timestamp=2000,
            content="v2-updated",
            metadata=None,
            topic_key="bug2-test",
            project="testproj",
        )
        obs_repo.upsert_topic_key(updated)

        mutations = sync_repo.get_mutations_since(0)
        # Should have insert + update
        ops = [m.op for m in mutations]
        assert "insert" in ops
        assert "update" in ops

        update_mut = [m for m in mutations if m.op == "update"][0]
        assert update_mut.entity_key == "bug2-test"

        conn.close()

    def test_upsert_topic_key_mutation_payload_has_content(self) -> None:
        """Mutation payload must contain the updated content."""
        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)

        obs_repo.create(_make_obs("tk-p", "original", topic_key="payload-test", project="testproj"))

        import json
        updated = Observation(
            id="tk-p",
            timestamp=2000,
            content="updated-content",
            metadata={"key": "val"},
            topic_key="payload-test",
            project="testproj",
        )
        obs_repo.upsert_topic_key(updated)

        mutations = sync_repo.get_mutations_since(0)
        update_mut = [m for m in mutations if m.op == "update"][0]
        payload = json.loads(update_mut.payload)
        assert payload["content"] == "updated-content"
        assert payload["topic_key"] == "payload-test"

        conn.close()


# ---------------------------------------------------------------------------
# Bug 1: Echo loop prevention
# ---------------------------------------------------------------------------

class TestEchoLoopPrevention:
    """Import must not create ghost mutations that get re-exported."""

    def test_disable_mutation_recording_prevents_mutations(self) -> None:
        """When recording is disabled, create() does not record mutations."""
        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)

        obs_repo.disable_mutation_recording()
        obs_repo.create(_make_obs("ghost-1", "should not mutate"))

        mutations = sync_repo.get_mutations_since(0)
        assert len(mutations) == 0

        # Re-enable and verify recording works again
        obs_repo.enable_mutation_recording()
        obs_repo.create(_make_obs("live-1", "should mutate"))

        mutations = sync_repo.get_mutations_since(0)
        assert len(mutations) == 1
        assert mutations[0].op == "insert"

        conn.close()

    def test_disable_suppresses_upsert_mutations(self) -> None:
        """When recording is disabled, upsert_topic_key does not record mutations."""
        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)

        # Create with recording ON
        obs_repo.create(_make_obs("ghost-tk", "v1", topic_key="echo-test", project="testproj"))

        # Disable and upsert
        obs_repo.disable_mutation_recording()
        updated = Observation(
            id="ghost-tk",
            timestamp=2000,
            content="v2",
            metadata=None,
            topic_key="echo-test",
            project="testproj",
        )
        obs_repo.upsert_topic_key(updated)

        mutations = sync_repo.get_mutations_since(0)
        # Only the original insert, no update mutation
        assert len(mutations) == 1
        assert mutations[0].op == "insert"

        conn.close()

    def test_import_mutations_does_not_create_ghost_mutations(self) -> None:
        """Importing mutations into DB-B must not create new mutations in DB-B."""
        from src.application.services.sync.sync_service import SyncService

        # DB-A: create data and export
        conn_a, db_a = _make_test_db()
        obs_a, sync_a = _wire_repos(db_a)
        svc_a = SyncService(
            observation_repo=obs_a,
            sync_repo=sync_a,
            export_dir=Path(tempfile.mkdtemp()) / "sync",
        )

        obs_a.create(_make_obs("echo-1", "from A"))
        obs_a.create(_make_obs("echo-2", "from A"))
        chunks = svc_a.export_incremental()

        # DB-B: import
        conn_b, db_b = _make_test_db()
        obs_b, sync_b = _wire_repos(db_b)
        svc_b = SyncService(
            observation_repo=obs_b,
            sync_repo=sync_b,
            export_dir=Path(tempfile.mkdtemp()) / "sync",
        )

        svc_b.import_mutations(chunks, source="test")

        # DB-B must have 0 mutations (no ghost mutations)
        mutations_b = sync_b.get_mutations_since(0)
        assert len(mutations_b) == 0

        # DB-B must have the imported data
        imported = obs_b.get_all()
        assert len(imported) == 2

        conn_a.close()
        conn_b.close()

    def test_import_observations_does_not_create_ghost_mutations(self) -> None:
        """Importing observations must not create ghost mutations."""
        from src.application.services.sync.sync_service import SyncService

        conn_a, db_a = _make_test_db()
        obs_a, sync_a = _wire_repos(db_a)
        svc_a = SyncService(
            observation_repo=obs_a,
            sync_repo=sync_a,
            export_dir=Path(tempfile.mkdtemp()) / "sync",
        )

        obs_a.create(_make_obs("full-echo-1", "full import test"))
        chunks = svc_a.export_observations()

        conn_b, db_b = _make_test_db()
        obs_b, sync_b = _wire_repos(db_b)
        svc_b = SyncService(
            observation_repo=obs_b,
            sync_repo=sync_b,
            export_dir=Path(tempfile.mkdtemp()) / "sync",
        )

        svc_b.import_observations(chunks, source="test")

        mutations_b = sync_b.get_mutations_since(0)
        assert len(mutations_b) == 0

        imported = obs_b.get_all()
        assert len(imported) == 1

        conn_a.close()
        conn_b.close()
