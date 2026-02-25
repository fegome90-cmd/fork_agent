"""Unit tests for ObservationRepository.

TDD Red Phase: These tests define the expected behavior BEFORE implementation.
All tests should FAIL initially until the repository is implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.exceptions import ObservationNotFoundError, RepositoryError
from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations


class TestObservationRepositoryCreate:
    """Tests for ObservationRepository.create operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_create_stores_observation(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="test-id-001",
            timestamp=1700000000000,
            content="Test observation",
            metadata={"key": "value"},
        )

        repo.create(observation)

        with db_connection as conn:
            cursor = conn.execute("SELECT * FROM observations WHERE id = ?", (observation.id,))
            row = cursor.fetchone()

        assert row is not None
        assert row["id"] == observation.id
        assert row["timestamp"] == observation.timestamp
        assert row["content"] == observation.content

    def test_create_raises_error_on_duplicate_id(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="duplicate-id",
            timestamp=1700000000000,
            content="First observation",
        )

        repo.create(observation)

        duplicate = Observation(
            id="duplicate-id",
            timestamp=1700000001000,
            content="Second observation",
        )

        with pytest.raises(RepositoryError):
            repo.create(duplicate)

    def test_create_syncs_to_fts(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="fts-test-001",
            timestamp=1700000000000,
            content="Unique searchable content for FTS test",
        )

        repo.create(observation)

        with db_connection as conn:
            cursor = conn.execute(
                "SELECT * FROM observations_fts WHERE observations_fts MATCH ?",
                ("searchable",),
            )
            row = cursor.fetchone()

        assert row is not None


class TestObservationRepositoryGetById:
    """Tests for ObservationRepository.get_by_id operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_get_by_id_returns_observation(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="get-test-001",
            timestamp=1700000000000,
            content="Test content",
            metadata={"source": "test"},
        )
        repo.create(observation)

        result = repo.get_by_id("get-test-001")

        assert result.id == observation.id
        assert result.timestamp == observation.timestamp
        assert result.content == observation.content
        assert result.metadata == observation.metadata

    def test_get_by_id_raises_not_found(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)

        with pytest.raises(ObservationNotFoundError):
            repo.get_by_id("non-existent-id")


class TestObservationRepositoryGetAll:
    """Tests for ObservationRepository.get_all operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_get_all_returns_empty_list_when_empty(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)

        result = repo.get_all()

        assert result == []

    def test_get_all_returns_all_observations(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        obs1 = Observation(id="all-001", timestamp=1700000000000, content="First")
        obs2 = Observation(id="all-002", timestamp=1700000001000, content="Second")
        repo.create(obs1)
        repo.create(obs2)

        result = repo.get_all()

        assert len(result) == 2
        assert result[0].id == "all-002"
        assert result[1].id == "all-001"


class TestObservationRepositoryUpdate:
    """Tests for ObservationRepository.update operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_update_modifies_observation(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="update-001",
            timestamp=1700000000000,
            content="Original content",
        )
        repo.create(observation)

        updated = Observation(
            id="update-001",
            timestamp=1700000001000,
            content="Updated content",
            metadata={"updated": True},
        )
        repo.update(updated)

        result = repo.get_by_id("update-001")
        assert result.content == "Updated content"
        assert result.timestamp == 1700000001000
        assert result.metadata == {"updated": True}

    def test_update_raises_not_found(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="non-existent",
            timestamp=1700000000000,
            content="Test",
        )

        with pytest.raises(ObservationNotFoundError):
            repo.update(observation)


class TestObservationRepositoryDelete:
    """Tests for ObservationRepository.delete operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_delete_removes_observation(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        observation = Observation(
            id="delete-001",
            timestamp=1700000000000,
            content="To be deleted",
        )
        repo.create(observation)

        repo.delete("delete-001")

        with pytest.raises(ObservationNotFoundError):
            repo.get_by_id("delete-001")

    def test_delete_raises_not_found(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)

        with pytest.raises(ObservationNotFoundError):
            repo.delete("non-existent-id")


class TestObservationRepositorySearch:
    """Tests for ObservationRepository.search operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_search_returns_matching_observations(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(
            Observation(id="search-001", timestamp=1700000000000, content="Python programming")
        )
        repo.create(
            Observation(id="search-002", timestamp=1700000001000, content="Java development")
        )
        repo.create(Observation(id="search-003", timestamp=1700000002000, content="Python testing"))

        result = repo.search("Python")

        assert len(result) == 2

    def test_search_with_limit(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(
            Observation(id="limit-001", timestamp=1700000000000, content="test content one")
        )
        repo.create(
            Observation(id="limit-002", timestamp=1700000001000, content="test content two")
        )
        repo.create(
            Observation(id="limit-003", timestamp=1700000002000, content="test content three")
        )

        result = repo.search("test", limit=2)

        assert len(result) == 2

    def test_search_returns_empty_when_no_match(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)

        result = repo.search("nonexistent")

        assert result == []


class TestObservationRepositoryTimestampRange:
    """Tests for ObservationRepository.get_by_timestamp_range operation."""

    @pytest.fixture
    def db_connection(self, tmp_path: Path) -> DatabaseConnection:
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        migrations_dir = (
            Path(__file__).parent.parent.parent.parent / "src/infrastructure/persistence/migrations"
        )
        run_migrations(config, migrations_dir)
        return DatabaseConnection(config)

    def test_get_by_timestamp_range_returns_observations(
        self, db_connection: DatabaseConnection
    ) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        repo.create(Observation(id="range-001", timestamp=1000, content="First"))
        repo.create(Observation(id="range-002", timestamp=2000, content="Second"))
        repo.create(Observation(id="range-003", timestamp=3000, content="Third"))
        repo.create(Observation(id="range-004", timestamp=4000, content="Fourth"))

        result = repo.get_by_timestamp_range(1500, 3500)

        assert len(result) == 2
        assert result[0].id == "range-003"
        assert result[1].id == "range-002"

    def test_get_by_timestamp_range_returns_empty_when_no_match(
        self, db_connection: DatabaseConnection
    ) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)

        result = repo.get_by_timestamp_range(1000, 2000)

        assert result == []


class TestObservationRepositoryErrorHandling:
    """Tests for ObservationRepository error handling."""

    def setup_method(self) -> None:
        DatabaseConnection.close_all()

    @pytest.fixture
    def failing_db_path(self, tmp_path: Path) -> Path:
        # Use a path to a non-writable location to cause actual database errors
        # Using a subdirectory that doesn't exist will cause sqlite3.OperationalError
        return tmp_path / "nonexistent_dir" / "corrupted.db"

    def test_create_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)
        observation = Observation(
            id="error-test",
            timestamp=1700000000000,
            content="Test",
        )

        with pytest.raises(RepositoryError):
            repo.create(observation)

    def test_get_by_id_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)

        with pytest.raises(RepositoryError):
            repo.get_by_id("test-id")

    def test_get_all_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)

        with pytest.raises(RepositoryError):
            repo.get_all()

    def test_update_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)
        observation = Observation(
            id="error-test",
            timestamp=1700000000000,
            content="Test",
        )

        with pytest.raises(RepositoryError):
            repo.update(observation)

    def test_delete_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)

        with pytest.raises(RepositoryError):
            repo.delete("test-id")

    def test_search_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)

        with pytest.raises(RepositoryError):
            repo.search("test")

    def test_get_by_timestamp_range_handles_database_error(self, failing_db_path: Path) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        config = DatabaseConfig(db_path=failing_db_path)
        connection = DatabaseConnection(config)
        repo = ObservationRepository(connection)

        with pytest.raises(RepositoryError):
            repo.get_by_timestamp_range(1000, 2000)
