"""Tests for incremental sync: mutation tracking, export/import, git backend."""

from __future__ import annotations

import gzip
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.domain.entities.observation import Observation
from src.domain.entities.sync import SyncChunk, SyncMutation, SyncStatus
from src.infrastructure.sync.git_sync import GitSyncBackend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs(
    obs_id: str = "test-1", content: str = "hello", obs_type: str | None = None
) -> Observation:
    return Observation(
        id=obs_id,
        timestamp=1000,
        content=content,
        metadata=None,
        type=obs_type,
        project=None,
    )


def _make_test_db() -> tuple[sqlite3.Connection, Path]:
    """Create an in-memory DB with sync tables."""
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    conn = sqlite3.connect(str(tmp))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Create observations table
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
    # Create FTS
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
            content, metadata, title, topic_key, content=observations, content_rowid=rowid
        )
    """)
    # Create sync tables
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


# ---------------------------------------------------------------------------
# Mutation entity validation
# ---------------------------------------------------------------------------


class TestSyncEntities:
    def test_sync_chunk_valid(self) -> None:
        chunk = SyncChunk(
            chunk_id="c1",
            source="local",
            imported_at=100,
            observation_count=5,
            checksum="sha256:abc",
        )
        assert chunk.chunk_id == "c1"

    def test_sync_chunk_empty_id_fails(self) -> None:
        with pytest.raises(ValueError, match="chunk_id cannot be empty"):
            SyncChunk(
                chunk_id="", source="local", imported_at=100, observation_count=5, checksum="abc"
            )

    def test_sync_mutation_valid(self) -> None:
        m = SyncMutation(
            seq=1,
            entity="observation",
            entity_key="id1",
            op="insert",
            payload="{}",
            source="local",
            project="",
            created_at=100,
        )
        assert m.op == "insert"

    def test_sync_mutation_bad_op_fails(self) -> None:
        with pytest.raises(ValueError, match="op must be one of"):
            SyncMutation(
                seq=1,
                entity="obs",
                entity_key="k",
                op="replace",
                payload="{}",
                source="local",
                project="",
                created_at=100,
            )

    def test_sync_status_defaults(self) -> None:
        s = SyncStatus()
        assert s.last_export_at is None
        assert s.last_export_seq == 0


# ---------------------------------------------------------------------------
# Mutation tracking via observation repo
# ---------------------------------------------------------------------------


class TestMutationTracking:
    def test_create_records_mutation(self) -> None:
        """When sync_repo is wired, create() records an insert mutation."""
        conn, db_path = _make_test_db()
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        db_conn = DatabaseConnection(config=DatabaseConfig(db_path=db_path))
        sync_repo = SyncRepositoryImpl(connection=db_conn)
        obs_repo = ObservationRepository(connection=db_conn, sync_repo=sync_repo)

        obs = _make_obs("mut-1", "test content")
        obs_repo.create(obs)

        # Verify mutation recorded
        mutations = sync_repo.get_mutations_since(0)
        assert len(mutations) == 1
        assert mutations[0].op == "insert"
        assert mutations[0].entity_key == "mut-1"

        conn.close()

    def test_delete_records_mutation(self) -> None:
        """Delete records a 'delete' mutation."""
        conn, db_path = _make_test_db()
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        db_conn = DatabaseConnection(config=DatabaseConfig(db_path=db_path))
        sync_repo = SyncRepositoryImpl(connection=db_conn)
        obs_repo = ObservationRepository(connection=db_conn, sync_repo=sync_repo)

        obs = _make_obs("del-1", "to be deleted")
        obs_repo.create(obs)
        obs_repo.delete("del-1")

        mutations = sync_repo.get_mutations_since(0)
        assert len(mutations) == 2
        assert mutations[1].op == "delete"
        assert mutations[1].entity_key == "del-1"

        conn.close()

    def test_no_sync_repo_no_crash(self) -> None:
        """Without sync_repo, operations work normally (no mutation tracking)."""
        conn, db_path = _make_test_db()
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        db_conn = DatabaseConnection(config=DatabaseConfig(db_path=db_path))
        obs_repo = ObservationRepository(connection=db_conn)

        obs = _make_obs("no-sync-1", "works fine")
        obs_repo.create(obs)  # Should NOT crash
        result = obs_repo.get_by_id("no-sync-1")
        assert result.id == "no-sync-1"

        conn.close()


# ---------------------------------------------------------------------------
# Incremental export/import
# ---------------------------------------------------------------------------


class TestIncrementalSync:
    def test_export_incremental_empty(self, tmp_path: Path) -> None:
        """No mutations → no chunks."""
        from src.application.services.sync.sync_service import SyncService
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        conn, db_path = _make_test_db()
        db_conn = DatabaseConnection(config=DatabaseConfig(db_path=db_path))
        sync_repo = SyncRepositoryImpl(connection=db_conn)
        obs_repo = ObservationRepository(connection=db_conn, sync_repo=sync_repo)
        service = SyncService(
            observation_repo=obs_repo, sync_repo=sync_repo, export_dir=tmp_path / "sync"
        )

        paths = service.export_incremental()
        assert paths == []
        conn.close()

    def test_export_then_import_roundtrip(self, tmp_path: Path) -> None:
        """Export mutations from DB-A, import into DB-B, verify data matches."""
        from src.application.services.sync.sync_service import SyncService
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        # --- DB-A: create data and export ---
        conn_a, db_a = _make_test_db()
        db_conn_a = DatabaseConnection(config=DatabaseConfig(db_path=db_a))
        sync_a = SyncRepositoryImpl(connection=db_conn_a)
        obs_a = ObservationRepository(connection=db_conn_a, sync_repo=sync_a)
        svc_a = SyncService(observation_repo=obs_a, sync_repo=sync_a, export_dir=tmp_path / "sync")

        obs_a.create(_make_obs("rt-1", "first obs"))
        obs_a.create(_make_obs("rt-2", "second obs"))

        chunks = svc_a.export_incremental()
        assert len(chunks) >= 1
        conn_a.close()

        # --- DB-B: import ---
        conn_b, db_b = _make_test_db()
        db_conn_b = DatabaseConnection(config=DatabaseConfig(db_path=db_b))
        sync_b = SyncRepositoryImpl(connection=db_conn_b)
        obs_b = ObservationRepository(connection=db_conn_b, sync_repo=sync_b)
        svc_b = SyncService(observation_repo=obs_b, sync_repo=sync_b, export_dir=tmp_path / "sync")

        counts = svc_b.import_mutations(chunks, source="test")
        assert counts["inserted"] == 2

        # Verify data
        imported = obs_b.get_all()
        assert len(imported) == 2
        contents = {o.id: o.content for o in imported}
        assert contents["rt-1"] == "first obs"
        assert contents["rt-2"] == "second obs"
        conn_b.close()

    def test_import_skips_duplicate_chunk(self, tmp_path: Path) -> None:
        """Importing the same chunk twice is a no-op."""
        from src.application.services.sync.sync_service import SyncService
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        conn_a, db_a = _make_test_db()
        db_conn_a = DatabaseConnection(config=DatabaseConfig(db_path=db_a))
        sync_a = SyncRepositoryImpl(connection=db_conn_a)
        obs_a = ObservationRepository(connection=db_conn_a, sync_repo=sync_a)
        svc_a = SyncService(observation_repo=obs_a, sync_repo=sync_a, export_dir=tmp_path / "sync")

        obs_a.create(_make_obs("dup-1", "dup content"))
        chunks = svc_a.export_incremental()

        # Import once
        conn_b, db_b = _make_test_db()
        db_conn_b = DatabaseConnection(config=DatabaseConfig(db_path=db_b))
        sync_b = SyncRepositoryImpl(connection=db_conn_b)
        obs_b = ObservationRepository(connection=db_conn_b, sync_repo=sync_b)
        svc_b = SyncService(observation_repo=obs_b, sync_repo=sync_b, export_dir=tmp_path / "sync")

        svc_b.import_mutations(chunks)
        assert len(obs_b.get_all()) == 1

        # Import again — should be skipped
        svc_b.import_mutations(chunks)
        assert len(obs_b.get_all()) == 1  # No duplicates
        conn_a.close()
        conn_b.close()

    def test_import_handles_delete_mutation(self, tmp_path: Path) -> None:
        """Delete mutations remove observations from target."""
        from src.application.services.sync.sync_service import SyncService
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        conn_a, db_a = _make_test_db()
        db_conn_a = DatabaseConnection(config=DatabaseConfig(db_path=db_a))
        sync_a = SyncRepositoryImpl(connection=db_conn_a)
        obs_a = ObservationRepository(connection=db_conn_a, sync_repo=sync_a)
        svc_a = SyncService(observation_repo=obs_a, sync_repo=sync_a, export_dir=tmp_path / "sync")

        obs_a.create(_make_obs("del-target", "will be deleted"))
        obs_a.delete("del-target")
        chunks = svc_a.export_incremental()

        # Import into B
        conn_b, db_b = _make_test_db()
        db_conn_b = DatabaseConnection(config=DatabaseConfig(db_path=db_b))
        sync_b = SyncRepositoryImpl(connection=db_conn_b)
        obs_b = ObservationRepository(connection=db_conn_b, sync_repo=sync_b)
        svc_b = SyncService(observation_repo=obs_b, sync_repo=sync_b, export_dir=tmp_path / "sync")

        # Pre-populate B with the same observation
        obs_b_no_sync = ObservationRepository(connection=db_conn_b)
        obs_b_no_sync.create(_make_obs("del-target", "will be deleted"))

        counts = svc_b.import_mutations(chunks)
        assert counts["deleted"] == 1
        assert len(obs_b.get_all()) == 0
        conn_a.close()
        conn_b.close()

    def test_second_export_is_noop(self, tmp_path: Path) -> None:
        """After export, subsequent export returns no new chunks."""
        from src.application.services.sync.sync_service import SyncService
        from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )
        from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

        conn, db = _make_test_db()
        db_conn = DatabaseConnection(config=DatabaseConfig(db_path=db))
        sync_repo = SyncRepositoryImpl(connection=db_conn)
        obs_repo = ObservationRepository(connection=db_conn, sync_repo=sync_repo)
        svc = SyncService(
            observation_repo=obs_repo, sync_repo=sync_repo, export_dir=tmp_path / "sync"
        )

        obs_repo.create(_make_obs("inc-1", "once"))
        chunks1 = svc.export_incremental()
        assert len(chunks1) >= 1

        chunks2 = svc.export_incremental()
        assert chunks2 == []
        conn.close()


# ---------------------------------------------------------------------------
# GitSyncBackend
# ---------------------------------------------------------------------------


class TestGitSyncBackend:
    @pytest.fixture(autouse=True)
    def _deterministic_git_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keep Git tests independent from the host global git config."""
        git_config = tmp_path / "gitconfig"
        git_config.write_text(
            "[init]\n"
            "\tdefaultBranch = main\n"
            "[user]\n"
            "\tname = Test User\n"
            "\temail = test@example.invalid\n"
        )
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(git_config))
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def test_init_repo(self, tmp_path: Path) -> None:
        git = GitSyncBackend(sync_dir=tmp_path)
        git.init_repo()
        assert (tmp_path / ".git").exists()

    def test_push_and_pull(self, tmp_path: Path) -> None:
        """Simulate push then pull with a bare remote repo."""
        import subprocess

        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()

        # Create bare remote first
        bare_remote = tmp_path / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(bare_remote)],
            check=True,
            capture_output=True,
        )

        git = GitSyncBackend(sync_dir=sync_dir, remote_url=str(bare_remote))
        git.init_repo()

        # Create a fake chunk
        chunk = sync_dir / "test.jsonl.gz"
        with gzip.open(chunk, "wt") as f:
            f.write('{"test": true}\n')

        ok = git.push([chunk])
        assert ok is True

        # Status should show branch
        info = git.status()
        assert info["branch"] == "main"

    def test_pull_no_remote_returns_empty(self, tmp_path: Path) -> None:
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        git = GitSyncBackend(sync_dir=sync_dir)
        git.init_repo()

        result = git.pull()
        assert result == []

    def test_status_no_remote(self, tmp_path: Path) -> None:
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        git = GitSyncBackend(sync_dir=sync_dir)
        git.init_repo()

        info = git.status()
        assert info["remote"] in ("none", "")
        assert info["branch"] == "main"
