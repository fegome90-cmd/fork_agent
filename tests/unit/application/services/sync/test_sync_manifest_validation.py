"""Tests for manifest checksum validation on import.

Bug 3: import_observations() and import_mutations() must validate
the manifest checksum before processing chunks.
"""

from __future__ import annotations

import gzip
import json
import sqlite3
import tempfile
from pathlib import Path

from src.domain.entities.observation import Observation


def _make_obs(
    obs_id: str = "test-1",
    content: str = "hello",
) -> Observation:
    return Observation(
        id=obs_id,
        timestamp=1000,
        content=content,
        metadata=None,
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


def _write_obs_chunk(
    export_dir: Path, observations: list[Observation], chunk_id: str = "sync_1000_000"
) -> Path:
    """Write a single observation chunk file."""
    export_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = export_dir / f"{chunk_id}.jsonl.gz"
    lines = []
    for obs in observations:
        lines.append(
            json.dumps(
                {
                    "id": obs.id,
                    "timestamp": obs.timestamp,
                    "content": obs.content,
                    "metadata": obs.metadata,
                    "idempotency_key": obs.idempotency_key,
                    "project": obs.project,
                    "type": obs.type,
                    "topic_key": obs.topic_key,
                    "revision_count": obs.revision_count,
                    "session_id": obs.session_id,
                },
                separators=(",", ":"),
            )
        )
    content = "\n".join(lines).encode("utf-8")
    with gzip.open(chunk_path, "wb") as f:
        f.write(content)
    return chunk_path


def _write_manifest(
    export_dir: Path, chunk_paths: list[Path], valid: bool = True, timestamp: int = 1000
) -> Path:
    """Write a manifest file with checksum over chunks."""
    import hashlib

    if valid:
        hasher = hashlib.sha256()
        for cp in chunk_paths:
            with open(cp, "rb") as f:
                hasher.update(f.read())
        checksum = f"sha256:{hasher.hexdigest()}"
    else:
        checksum = "sha256:deadbeef00000000000000000000000000000000000000000000000000000000"

    manifest_path = export_dir / f"manifest_{timestamp}.json"
    manifest = {
        "chunk_count": len(chunk_paths),
        "total_observations": 1,
        "checksum": checksum,
        "created_at": timestamp,
        "export_version": 1,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest_path


class TestManifestValidationObservations:
    """Manifest checksum validation for import_observations."""

    def test_import_valid_manifest_passes(self) -> None:
        """Import with valid manifest checksum should succeed."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = Path(tempfile.mkdtemp()) / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        obs = _make_obs("mv-1", "valid manifest test")
        chunk_path = _write_obs_chunk(export_dir, [obs])
        manifest_path = _write_manifest(export_dir, [chunk_path], valid=True)

        count = svc.import_observations([chunk_path], source="test", manifest_path=manifest_path)
        assert count == 1

        conn.close()

    def test_import_tampered_manifest_fails(self) -> None:
        """Import with tampered chunk should raise ValueError."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = Path(tempfile.mkdtemp()) / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        obs = _make_obs("mv-2", "tampered test")
        chunk_path = _write_obs_chunk(export_dir, [obs])
        # Write manifest with WRONG checksum
        manifest_path = _write_manifest(export_dir, [chunk_path], valid=False)

        import pytest

        with pytest.raises(ValueError, match="checksum mismatch"):
            svc.import_observations([chunk_path], source="test", manifest_path=manifest_path)

        conn.close()

    def test_import_without_manifest_skips_validation(self) -> None:
        """Import without manifest_path should succeed (backward compat)."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = Path(tempfile.mkdtemp()) / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        obs = _make_obs("mv-3", "no manifest test")
        chunk_path = _write_obs_chunk(export_dir, [obs])

        count = svc.import_observations([chunk_path], source="test")
        assert count == 1

        conn.close()

    def test_import_missing_manifest_file_skips_validation(self) -> None:
        """Import with non-existent manifest_path should succeed."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = Path(tempfile.mkdtemp()) / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        obs = _make_obs("mv-4", "missing manifest test")
        chunk_path = _write_obs_chunk(export_dir, [obs])

        missing_manifest = export_dir / "nonexistent_manifest.json"
        count = svc.import_observations([chunk_path], source="test", manifest_path=missing_manifest)
        assert count == 1

        conn.close()


class TestManifestValidationMutations:
    """Manifest checksum validation for import_mutations."""

    def _write_mutation_chunk(
        self, export_dir: Path, mutations: list[dict], chunk_id: str = "mutation_1000_000"
    ) -> Path:
        """Write a single mutation chunk file."""
        chunk_path = export_dir / f"{chunk_id}.jsonl.gz"
        export_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(chunk_path, "wt", encoding="utf-8") as f:
            for m in mutations:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        return chunk_path

    def test_import_mutations_valid_manifest(self) -> None:
        """Import mutations with valid manifest should succeed."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = Path(tempfile.mkdtemp()) / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        mutation = {
            "seq": 1,
            "entity": "observation",
            "entity_key": "mm-1",
            "op": "insert",
            "payload": json.dumps({"id": "mm-1", "timestamp": 1000, "content": "test"}),
            "source": "local",
            "project": "",
            "created_at": 1000,
        }
        chunk_path = self._write_mutation_chunk(export_dir, [mutation])
        manifest_path = _write_manifest(export_dir, [chunk_path], valid=True)

        counts = svc.import_mutations([chunk_path], source="test", manifest_path=manifest_path)
        assert counts["inserted"] == 1

        conn.close()

    def test_import_mutations_tampered_manifest_fails(self) -> None:
        """Import mutations with tampered chunk should raise ValueError."""
        from src.application.services.sync.sync_service import SyncService

        conn, db_path = _make_test_db()
        obs_repo, sync_repo = _wire_repos(db_path)
        export_dir = Path(tempfile.mkdtemp()) / "sync"
        svc = SyncService(observation_repo=obs_repo, sync_repo=sync_repo, export_dir=export_dir)

        mutation = {
            "seq": 1,
            "entity": "observation",
            "entity_key": "mm-2",
            "op": "insert",
            "payload": json.dumps({"id": "mm-2", "timestamp": 1000, "content": "test"}),
            "source": "local",
            "project": "",
            "created_at": 1000,
        }
        chunk_path = self._write_mutation_chunk(export_dir, [mutation])
        manifest_path = _write_manifest(export_dir, [chunk_path], valid=False)

        import pytest

        with pytest.raises(ValueError, match="checksum mismatch"):
            svc.import_mutations([chunk_path], source="test", manifest_path=manifest_path)

        conn.close()
