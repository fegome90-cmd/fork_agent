"""Dependency injection container for persistence layer."""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from src.application.services.cleanup_service import CleanupService
from src.application.services.memory_service import MemoryService
from src.application.services.scheduler_service import SchedulerService
from src.application.services.telemetry.telemetry_service import TelemetryService

from src.application.services.workspace.entities import LayoutType, WorkspaceConfig
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.health_check import HealthCheckService
from src.infrastructure.persistence.migrations import MigrationRunner, run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.persistence.repositories.scheduled_task_repository import (
    ScheduledTaskRepository,
)
from src.infrastructure.persistence.repositories.telemetry_repository import (
    TelemetryRepositoryImpl,
)

from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

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

    cleanup_service = providers.Singleton(
        CleanupService,
        connection=database_connection,
    )

    health_check_service = providers.Singleton(
        HealthCheckService,
        connection=database_connection,
        db_path=config.db_path,
    )

    tmux_orchestrator = providers.Singleton(
        TmuxOrchestrator,
        safety_mode=False,
    )

    telemetry_repository = providers.Singleton(
        TelemetryRepositoryImpl,
        connection=database_connection,
    )

    telemetry_service = providers.Singleton(
        TelemetryService,
        repository=telemetry_repository,
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


# =============================================================================
# Convenience Factory Functions
# =============================================================================

# Global container instance for convenience functions
_global_container: Container | None = None

# Global singleton instances for non-container services
_workspace_manager: WorkspaceManager | None = None

def _get_global_container() -> Container:
    """Get or create the global container instance."""
    global _global_container
    if _global_container is None:
        _global_container = create_container()
    return _global_container


def get_tmux_orchestrator() -> TmuxOrchestrator:
    """Get the singleton TmuxOrchestrator instance.

    Returns:
        TmuxOrchestrator: The singleton orchestrator instance.
    """
    return _get_global_container().tmux_orchestrator()  # type: ignore[no-any-return]


def get_memory_service(db_path: Path | None = None) -> MemoryService:
    """Get a MemoryService instance.

    Args:
        db_path: Optional database path. If None, uses default path.

    Returns:
        MemoryService: The memory service instance.
    """
    if db_path is not None:
        # Create a new container with custom db_path
        container = create_container(db_path)
        return container.memory_service()  # type: ignore[no-any-return]
    return _get_global_container().memory_service()  # type: ignore[no-any-return]


def get_workspace_manager() -> WorkspaceManager:
    """Get the singleton WorkspaceManager instance.

    Returns:
        WorkspaceManager: The workspace manager instance.
    """
    global _workspace_manager
    if _workspace_manager is None:
        git_executor = GitCommandExecutor()
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=None,
        )
        _workspace_manager = WorkspaceManager(git_executor, config)
    return _workspace_manager


def detect_memory_db_path() -> Path:
    """Detect the appropriate memory DB path based on current workspace.

    If we're in a worktree, use a worktree-specific DB path.
    Otherwise, use the default repo-level DB path.

    Returns:
        Path: The path to the memory database file.
    """
    try:
        workspace_manager = get_workspace_manager()
        workspace = workspace_manager.detect_workspace()

        if workspace is not None:
            # We're in a worktree - use worktree-specific DB
            worktree_db_dir = workspace.path / ".memory"
            worktree_db_dir.mkdir(parents=True, exist_ok=True)
            return worktree_db_dir / "observations.db"
    except Exception:
        # If workspace detection fails, fall through to default
        pass

    # Default: use repo-level DB
    return DEFAULT_DB_PATH


def get_memory_service_auto() -> MemoryService:
    """Get MemoryService with automatic workspace-aware DB path detection.

    This function automatically detects if we're in a worktree and uses
    the appropriate isolated database path.

    Returns:
        MemoryService: The memory service instance with correct DB path.
    """
    db_path = detect_memory_db_path()
    return get_memory_service(db_path)
