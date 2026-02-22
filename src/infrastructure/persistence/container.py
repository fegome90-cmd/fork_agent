"""Dependency injection container for persistence layer."""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from src.application.services.memory_service import MemoryService
from src.application.services.scheduler_service import SchedulerService
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import MigrationRunner, run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.persistence.repositories.scheduled_task_repository import (
    ScheduledTaskRepository,
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

    scheduled_task_repository = providers.Singleton(
        ScheduledTaskRepository,
        connection=database_connection,
    )

    memory_service = providers.Singleton(
        MemoryService,
        repository=observation_repository,
    )

    scheduler_service = providers.Singleton(
        SchedulerService,
        repository=scheduled_task_repository,
    )


def create_container(db_path: Path | None = None) -> Container:
    container = Container()
    db_path_value = db_path or DEFAULT_DB_PATH
    container.config.db_path.from_value(db_path_value)
    container.config.migrations_dir.from_value(DEFAULT_MIGRATIONS_DIR)
    _run_migrations_on_init(db_path_value, DEFAULT_MIGRATIONS_DIR)
    return container


def _run_migrations_on_init(db_path: Path, migrations_dir: Path) -> None:
    """Run pending migrations on container initialization."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    config = DatabaseConfig(db_path=db_path)
    run_migrations(config, migrations_dir)


def override_database_for_testing(container: Container, test_db_path: Path) -> None:
    container.config.db_path.override(test_db_path)
    container.database_config.reset()
