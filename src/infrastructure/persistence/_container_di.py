"""Heavy DI container — loaded only when advanced DI features are needed.

This module imports dependency_injector (~140ms overhead) and is deliberately
kept separate from the fast-path factory functions in container.py.
Import ONLY via container.get_container() or container.__getattr__().
"""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from src.application.services.cleanup_service import CleanupService
from src.application.services.memory_service import MemoryService
from src.application.services.messaging.agent_messenger import AgentMessenger
from src.application.services.orchestration.hook_service import HookService
from src.application.services.scheduler_service import SchedulerService
from src.application.services.session_service import SessionService
from src.application.services.sync.sync_service import SyncService
from src.application.services.telemetry.telemetry_service import TelemetryService
from src.application.services.workflow.executor import WorkflowExecutor
from src.application.services.workspace.entities import LayoutType, WorkspaceConfig
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator
from src.infrastructure.persistence.health_check import HealthCheckService
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.persistence.migrations import MigrationRunner
from src.infrastructure.persistence.repositories.observation_repository import ObservationRepository
from src.infrastructure.persistence.repositories.sync_repository import SyncRepositoryImpl
from src.infrastructure.persistence.repositories.telemetry_repository import TelemetryRepositoryImpl
from src.infrastructure.persistence.repositories.scheduled_task_repository import ScheduledTaskRepository
from src.infrastructure.persistence.repositories.session_repository import SessionRepositoryImpl
from src.infrastructure.persistence.repositories.promise_repository import PromiseContractRepository
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor
from src.infrastructure.persistence.container import (
    DEFAULT_DB_PATH,
    DEFAULT_MIGRATIONS_DIR,
    _auto_backup,
    _run_migrations_on_init,
    get_default_data_dir,
)


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

    sync_repository = providers.Singleton(
        SyncRepositoryImpl,
        connection=database_connection,
    )

    observation_repository = providers.Singleton(
        ObservationRepository,
        connection=database_connection,
        sync_repo=sync_repository,
    )

    scheduled_task_repository = providers.Singleton(
        ScheduledTaskRepository,
        connection=database_connection,
    )

    telemetry_repository = providers.Singleton(
        TelemetryRepositoryImpl,
        connection=database_connection,
    )

    telemetry_service = providers.Singleton(
        TelemetryService,
        repository=telemetry_repository,
    )
    session_repository = providers.Singleton(
        SessionRepositoryImpl,
        connection=database_connection,
    )

    session_service = providers.Singleton(
        SessionService,
        repository=session_repository,
    )

    memory_service = providers.Singleton(
        MemoryService,
        repository=observation_repository,
        telemetry_service=telemetry_service,
    )

    scheduler_service = providers.Singleton(
        SchedulerService,
        repository=scheduled_task_repository,
    )

    cleanup_service = providers.Singleton(
        CleanupService,
        connection=database_connection,
    )

    sync_service = providers.Singleton(
        SyncService,
        observation_repo=observation_repository,
        sync_repo=sync_repository,
        export_dir=get_default_data_dir() / "sync",
    )

    health_check_service = providers.Singleton(
        HealthCheckService,
        connection=database_connection,
        db_path=config.db_path,
    )

    promise_contract_repository = providers.Singleton(
        PromiseContractRepository,
        connection=database_connection,
    )

    tmux_orchestrator = providers.Singleton(
        TmuxOrchestrator,
        safety_mode=False,
    )

    message_repository = providers.Singleton(
        MessageStore,
        connection=database_connection,
    )

    agent_messenger = providers.Singleton(
        AgentMessenger,
        orchestrator=tmux_orchestrator,
        store=message_repository,
    )

    git_executor = providers.Singleton(GitCommandExecutor)

    workspace_config = providers.Singleton(
        WorkspaceConfig,
        default_layout=LayoutType.NESTED,
        auto_cleanup=True,
        hooks_dir=None,
    )

    workspace_manager = providers.Singleton(
        WorkspaceManager,
        git_executor=git_executor,
        config=workspace_config,
    )


def create_container(
    db_path: Path | None = None,
    export_dir: Path | None = None,
) -> Container:
    """Create and configure a new DI container."""
    container = Container()
    db_path_value = db_path or DEFAULT_DB_PATH
    container.config.db_path.from_value(db_path_value)
    container.config.migrations_dir.from_value(DEFAULT_MIGRATIONS_DIR)
    if export_dir is not None:
        container.sync_service.override(
            providers.Singleton(
                SyncService,
                observation_repo=container.observation_repository,
                sync_repo=container.sync_repository,
                export_dir=export_dir,
            )
        )
    _auto_backup(db_path_value)
    _run_migrations_on_init(db_path_value, DEFAULT_MIGRATIONS_DIR)
    return container


def override_database_for_testing(container: Container, test_db_path: Path) -> None:
    """Override database path for testing."""
    container.config.db_path.override(test_db_path)
    container.database_config.reset()

