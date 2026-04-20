"""Tests for snapshot (full) export/import roundtrip.

Validates export_observations and import_observations with various
chunk sizes, project filters, and field preservation.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from src.domain.entities.observation import Observation


def _make_obs(
    obs_id: str = "test-1",
    content: str = "hello",
    project: str | None = None,
    topic_key: str | None = None,
    obs_type: str | None = None,
    session_id: str | None = None,
    revision_count: int = 1,
) -> Observation:
    return Observation(
        id=obs_id,
        timestamp=1000,
        content=content,
        metadata={"k": "v"} if obs_id.endswith("-meta") else None,
        idempotency_key=f"ik-{obs_id}",
        project=project,
        type=obs_type,
        topic_key=topic_key,
        revision_count=revision_count,
        session_id=session_id,
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
# Snapshot export
# ---------------------------------------------------------------------------


class TestFullSnapshotExport:
    def test_full_snapshot_exports_all_observations(self, tmp_path: Path) -> None:
        """5 observations exported into 1 chunk with a manifest file."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = tmp_path / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        for i in range(5):
            obs_repo.create(_make_obs(f"sn-{i}", f"content-{i}"))

        chunks = svc.export_observations()
        assert len(chunks) == 1
        assert chunks[0].exists()
        assert chunks[0].suffix == ".gz"

        # Manifest should exist
        manifests = list(export_dir.glob("manifest_*.json"))
        assert len(manifests) == 1
        conn.close()

    def test_all_fields_survive_roundtrip(self, tmp_path: Path) -> None:
        """All 10 observation fields survive export+import roundtrip."""
        from src.application.services.sync.sync_service import SyncService

        # --- DB-A: create and export ---
        conn_a, db_a = _make_test_db()
        obs_a, sync_a = _wire_repos(db_a)
        export_dir = tmp_path / "sync"
        svc_a = SyncService(observation_repo=obs_a, sync_repo=sync_a, export_dir=export_dir)

        obs_a.create(
            Observation(
                id="fields-1",
                timestamp=9999,
                content="full field test",
                metadata={"env": "test", "version": 2},
                idempotency_key="ik-fields-1",
                project="myproject",
                type="decision",
                topic_key="myproject/decision-1",
                revision_count=3,
                session_id="sess-abc",
            )
        )

        chunks = svc_a.export_observations()
        assert len(chunks) == 1
        conn_a.close()

        # --- DB-B: import and verify ---
        conn_b, db_b = _make_test_db()
        obs_b, sync_b = _wire_repos(db_b)
        svc_b = SyncService(observation_repo=obs_b, sync_repo=sync_b, export_dir=export_dir)

        imported = svc_b.import_observations(chunks, source="test")
        assert imported == 1

        result = obs_b.get_by_id("fields-1")
        assert result.id == "fields-1"
        assert result.timestamp == 9999
        assert result.content == "full field test"
        assert result.metadata == {"env": "test", "version": 2}
        assert result.idempotency_key == "ik-fields-1"
        assert result.project == "myproject"
        assert result.type == "decision"
        assert result.topic_key == "myproject/decision-1"
        assert result.revision_count == 3
        assert result.session_id == "sess-abc"
        conn_b.close()

    def test_chunk_boundary_splits_correctly(self, tmp_path: Path) -> None:
        """7 observations with chunk_size=3 produces 3 chunks."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = tmp_path / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        for i in range(7):
            obs_repo.create(_make_obs(f"chunk-{i}", f"val-{i}"))

        chunks = svc.export_observations(chunk_size=3)
        assert len(chunks) == 3  # 3 + 3 + 1
        conn.close()

    def test_chunk_boundary_import_all_chunks(self, tmp_path: Path) -> None:
        """7 observations roundtrip with chunk_size=3 preserves all data."""
        from src.application.services.sync.sync_service import SyncService

        # --- DB-A: create and export with small chunks ---
        conn_a, db_a = _make_test_db()
        obs_a, sync_a = _wire_repos(db_a)
        export_dir = tmp_path / "sync"
        svc_a = SyncService(observation_repo=obs_a, sync_repo=sync_a, export_dir=export_dir)

        for i in range(7):
            obs_a.create(_make_obs(f"cb-{i}", f"cb-content-{i}"))

        chunks = svc_a.export_observations(chunk_size=3)
        assert len(chunks) == 3
        conn_a.close()

        # --- DB-B: import all 3 chunks ---
        conn_b, db_b = _make_test_db()
        obs_b, sync_b = _wire_repos(db_b)
        svc_b = SyncService(observation_repo=obs_b, sync_repo=sync_b, export_dir=export_dir)

        imported = svc_b.import_observations(chunks, source="test")
        assert imported == 7

        all_obs = obs_b.get_all()
        assert len(all_obs) == 7
        ids = {o.id for o in all_obs}
        for i in range(7):
            assert f"cb-{i}" in ids
        conn_b.close()

    def test_export_with_project_filter(self, tmp_path: Path) -> None:
        """Export only observations matching the project filter."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = tmp_path / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        for i in range(3):
            obs_repo.create(_make_obs(f"alpha-{i}", f"a{i}", project="alpha"))
        for i in range(2):
            obs_repo.create(_make_obs(f"beta-{i}", f"b{i}", project="beta"))

        chunks = svc.export_observations(project="alpha")
        assert len(chunks) == 1

        # Verify only alpha observations in chunk
        import gzip

        with gzip.open(chunks[0], "rt") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 3
        for line in lines:
            assert line["project"] == "alpha"
        conn.close()

    def test_export_empty_db_returns_no_chunks(self, tmp_path: Path) -> None:
        """Empty DB export returns empty list and no manifest."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = tmp_path / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        chunks = svc.export_observations()
        assert chunks == []

        manifests = list(export_dir.glob("manifest_*.json"))
        assert len(manifests) == 0
        conn.close()
