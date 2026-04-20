"""Tests for BUG-21/22: Upsert creates duplicates when project/type changes."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations


@pytest.fixture()
def db_connection(tmp_path: Path) -> DatabaseConnection:
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = (
        Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
    )
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config)


class TestBug21UpsertNoDuplicates:
    """BUG-21/22: Same topic_key with different project should update, not duplicate."""

    def test_upsert_changes_project(self, db_connection: DatabaseConnection) -> None:
        """BUG-21/22: Same topic_key with different project creates separate obs.

        With project-scoped topic_key lookup, saving with a different project
        does NOT update the existing cross-project observation — it creates a new one.
        This prevents cross-project contamination.
        """
        from src.application.services.memory_service import MemoryService
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        service = MemoryService(repository=repo)

        # First save with project A
        obs1 = service.save(
            content="upsert test content",
            topic_key="test/upsert-dup",
            project="project-a",
            type="decision",
        )

        # Second save with same topic_key but project B — creates NEW obs
        # (project-scoped: does NOT find project-a's obs)
        obs2 = service.save(
            content="upsert test content updated",
            topic_key="test/upsert-dup",
            project="project-b",
            type="pattern",
        )

        # Different observations — project-scoped prevents cross-project upsert
        assert obs2.id != obs1.id, "Different projects should create separate observations"
        assert obs2.project == "project-b"
        assert obs1.project == "project-a"

        # Verify both exist in DB
        all_obs = repo.get_all()
        matching = [o for o in all_obs if o.topic_key == "test/upsert-dup"]
        assert len(matching) == 2, f"Expected 2 (one per project), got {len(matching)}"

    def test_upsert_changes_type_only(self, db_connection: DatabaseConnection) -> None:
        from src.application.services.memory_service import MemoryService
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        service = MemoryService(repository=repo)

        obs1 = service.save(
            content="type change test",
            topic_key="test/type-change",
            type="discovery",
        )

        obs2 = service.save(
            content="type change test updated",
            topic_key="test/type-change",
            type="bugfix",
        )

        assert obs2.id == obs1.id
        assert obs2.type == "bugfix"
        assert obs2.revision_count == 2

        all_obs = repo.get_all()
        matching = [o for o in all_obs if o.topic_key == "test/type-change"]
        assert len(matching) == 1

    def test_upsert_no_project_to_project(self, db_connection: DatabaseConnection) -> None:
        from src.application.services.memory_service import MemoryService
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        service = MemoryService(repository=repo)

        obs1 = service.save(
            content="no project test",
            topic_key="test/no-proj",
        )

        obs2 = service.save(
            content="no project test updated",
            topic_key="test/no-proj",
            project="new-project",
        )

        assert obs2.id == obs1.id
        assert obs2.project == "new-project"

        all_obs = repo.get_all()
        matching = [o for o in all_obs if o.topic_key == "test/no-proj"]
        assert len(matching) == 1
