"""Edge case tests for sync pipeline — Phase 2.3 hardening."""

from __future__ import annotations

from pathlib import Path

from src.application.services.sync.sync_service import SyncService
from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / "src/infrastructure/persistence/migrations"
)


def _make_sync_service(
    tmp_path: Path, db_name: str = "test.db"
) -> tuple[SyncService, ObservationRepository, DatabaseConnection]:
    """Create a SyncService with real DB for testing."""
    db_path = tmp_path / db_name
    config = DatabaseConfig(db_path=db_path)
    run_migrations(config, MIGRATIONS_DIR)
    conn = DatabaseConnection(config)
    repo = ObservationRepository(conn)
    sync_repo = SyncRepositoryImpl(connection=conn)
    export_dir = tmp_path / "export"
    service = SyncService(observation_repo=repo, sync_repo=sync_repo, export_dir=export_dir)
    return service, repo, conn


def _make_obs(obs_id: str, content: str, **kwargs: object) -> Observation:
    return Observation(id=obs_id, timestamp=1000, content=content, **kwargs)  # type: ignore[arg-type]


class TestSyncEdgeCases:
    """Edge cases for sync export/import pipeline."""

    def test_export_empty_db(self, tmp_path: Path) -> None:
        """Export from empty database should produce valid manifest."""
        service, _repo, _conn = _make_sync_service(tmp_path)
        paths = service.export_observations()
        assert isinstance(paths, list)

    def test_import_empty_directory(self, tmp_path: Path) -> None:
        """Import from empty list should return 0 imported."""
        service, _repo, _conn = _make_sync_service(tmp_path)
        count = service.import_observations([])
        assert count == 0

    def test_export_import_roundtrip(self, tmp_path: Path) -> None:
        """Export 50 observations and import into fresh DB."""
        service, repo, _conn = _make_sync_service(tmp_path)

        for i in range(50):
            obs = _make_obs(f"obs-{i:04d}", f"Observation {i}", type="discovery", project="test")
            repo.create(obs)

        paths = service.export_observations()
        assert len(paths) > 0
        assert all(p.exists() for p in paths)

        # Import into fresh DB
        import_service, import_repo, _ = _make_sync_service(tmp_path / "import", "import.db")
        count = import_service.import_observations(paths)
        assert count == 50

        imported = import_repo.get_all()
        assert len(imported) == 50

    def test_export_with_unicode(self, tmp_path: Path) -> None:
        """Observations with unicode should export without errors."""
        service, repo, _conn = _make_sync_service(tmp_path)

        special_contents = [
            "Unicode: 日本語テスト ñ é ü",
            "Quotes: \"double\" 'single' `backtick`",
            "Newlines: line1\nline2\nline3",
            'JSON: {"key": "value", "num": 42}',
        ]

        for i, content in enumerate(special_contents):
            obs = _make_obs(f"special-{i}", content, type="pattern")
            repo.create(obs)

        paths = service.export_observations()
        assert len(paths) > 0
        # Verify export succeeded for all
        total_size = sum(p.stat().st_size for p in paths)
        assert total_size > 0

    def test_duplicate_import_idempotent(self, tmp_path: Path) -> None:
        """Importing same export twice should not create duplicates."""
        service, repo, _conn = _make_sync_service(tmp_path)

        obs = _make_obs("dup-test", "dup content", idempotency_key="dup-key")
        repo.create(obs)

        paths = service.export_observations()

        import_service, import_repo, _ = _make_sync_service(tmp_path / "import", "import.db")

        count1 = import_service.import_observations(paths)
        assert count1 == 1

        count2 = import_service.import_observations(paths)
        assert count2 == 0

        imported = import_repo.get_all()
        assert len(imported) == 1
