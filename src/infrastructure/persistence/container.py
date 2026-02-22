"""Dependency injection container for persistence layer."""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from src.application.services.memory_service import MemoryService
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import MigrationRunner
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)


DEFAULT_DB_PATH = Path("data/memory.db")
DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Container(containers.DeclarativeContainer):
    """Main DI container for persistence infrastructure."""

    config = providers.Configuration()

    database_config = providers.Singleton(
        DatabaseConfig,
        db_path=config.db_path,
    )

    database_connection = providers.Singleton(
        DatabaseConnection,
        config=database_config,
    )

    migration_runner = providers.Factory(
        MigrationRunner,
        config=database_config,
        migrations_dir=config.migrations_dir,
    )

    observation_repository = providers.Singleton(
        ObservationRepository,
        connection=database_connection,
    )

    memory_service = providers.Singleton(
        MemoryService,
        repository=observation_repository,
    )


def create_container(db_path: Path | None = None) -> Container:
    container = Container()
    container.config.db_path.from_value(db_path or DEFAULT_DB_PATH)
    container.config.migrations_dir.from_value(DEFAULT_MIGRATIONS_DIR)
    return container


def override_database_for_testing(container: Container, test_db_path: Path) -> None:
    container.config.db_path.override(test_db_path)
    container.database_config.reset()
