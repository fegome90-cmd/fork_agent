"""Tests for BUG-20: FTS5 search crashes on special characters."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.entities.observation import Observation
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


class TestBug20FtsSpecialChars:
    """BUG-20: FTS5 search should handle < > + = @ characters."""

    def test_search_angle_brackets(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(
            Observation(
                id="fts-angle-001",
                timestamp=1700000000000,
                content="Result<T,E> error handling pattern",
            )
        )

        result = repo.search("Result<T")
        assert len(result) == 1
        assert "Result<T,E>" in result[0].content

    def test_search_plus_equals(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(
            Observation(
                id="fts-plus-001",
                timestamp=1700000000000,
                content="operator+= and operator== in C++",
            )
        )

        result = repo.search("operator+=")
        assert len(result) == 1

    def test_search_at_sign(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(
            Observation(
                id="fts-at-001",
                timestamp=1700000000000,
                content="user@example.com email validation",
            )
        )

        result = repo.search("user@example")
        assert len(result) == 1

    def test_search_combined_special_chars(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(
            Observation(
                id="fts-combo-001",
                timestamp=1700000000000,
                content="Map<String, List<int>> nested generics",
            )
        )

        result = repo.search("Map<String")
        assert len(result) == 1
