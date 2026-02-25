"""Unit tests for dependency injection container."""

from pathlib import Path

from src.infrastructure.persistence.container import (
    Container,
    create_container,
    override_database_for_testing,
)


class TestContainer:
    """Tests for DI container."""

    def test_container_creates_database_config(self) -> None:
        container = Container()
        container.config.db_path.from_value(Path("data/test.db"))
        container.config.migrations_dir.from_value(Path("migrations"))
        config = container.database_config()

        assert config is not None
        assert hasattr(config, "db_path")
        assert hasattr(config, "journal_mode")

    def test_container_creates_database_connection(self) -> None:
        container = Container()
        container.config.db_path.from_value(Path("data/test.db"))
        container.config.migrations_dir.from_value(Path("migrations"))
        conn = container.database_connection()

        assert conn is not None

    def test_container_database_connection_is_singleton(self) -> None:
        container = Container()
        container.config.db_path.from_value(Path("data/test.db"))
        container.config.migrations_dir.from_value(Path("migrations"))
        conn1 = container.database_connection()
        conn2 = container.database_connection()

        assert conn1 is conn2

    def test_container_migration_runner(self) -> None:
        container = Container()
        container.config.db_path.from_value(Path("data/test.db"))
        container.config.migrations_dir.from_value(Path("migrations"))
        runner = container.migration_runner()

        assert runner is not None


class TestCreateContainer:
    """Tests for container factory function."""

    def test_create_container_returns_container(self) -> None:
        container = create_container()
        assert container.database_config() is not None

    def test_create_container_with_custom_db_path(self, tmp_path: Path) -> None:
        db_path = tmp_path / "custom.db"
        container = create_container(db_path=db_path)

        config = container.database_config()
        assert config.db_path == db_path


class TestOverrideForTesting:
    """Tests for test override functionality."""

    def test_override_database_for_testing(self, tmp_path: Path) -> None:
        container = create_container()
        test_db = tmp_path / "test.db"

        override_database_for_testing(container, test_db)

        config = container.database_config()
        assert config.db_path == test_db

    def test_override_returns_none(self, tmp_path: Path) -> None:
        container = create_container()
        test_db = tmp_path / "test.db"

        result = override_database_for_testing(container, test_db)

        assert result is None
