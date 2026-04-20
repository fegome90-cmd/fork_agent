"""Dependency injection container for persistence layer."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock

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
from src.infrastructure.persistence.health_check import HealthCheckService
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.persistence.migrations import MigrationRunner, run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.persistence.repositories.promise_repository import (
    PromiseContractRepository,
)
from src.infrastructure.persistence.repositories.scheduled_task_repository import (
    ScheduledTaskRepository,
)
from src.infrastructure.persistence.repositories.session_repository import (
    SessionRepositoryImpl,
)
from src.infrastructure.persistence.repositories.sync_repository import (
    SyncRepositoryImpl,
)
from src.infrastructure.persistence.repositories.telemetry_repository import (
    TelemetryRepositoryImpl,
)
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_default_data_dir() -> Path:
    """Return platform-specific data directory for fork.

    Checks FORK_DATA_DIR env var, then XDG_DATA_HOME, then platform default.
    Creates the directory if it does not exist.
    """
    if os.environ.get("FORK_DATA_DIR"):
        p = Path(os.environ["FORK_DATA_DIR"])
        p.mkdir(parents=True, exist_ok=True)
        return p
    xdg = os.environ.get("XDG_DATA_HOME", "")
    p = Path(xdg) / "fork" if xdg else Path.home() / ".local" / "share" / "fork"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_db_path() -> Path:
    """Return default DB path.

    Priority: FORK_MEMORY_DB env > XDG/fallback default.
    Parent directories are created automatically.
    """
    if os.environ.get("FORK_MEMORY_DB"):
        p = Path(os.environ["FORK_MEMORY_DB"])
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return get_default_data_dir() / "memory.db"


DEFAULT_DB_PATH = get_default_db_path()


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

    # Workspace infrastructure
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


def _auto_backup(db_path: Path) -> None:
    """Auto-backup DB before container init if DB exists and has data.

    Keeps at most 3 backups. Prevents catastrophic data loss from
    agent-triggered DB recreation (see P2 in subagent-failure-patterns.md).
    """
    if not db_path.exists():
        return
    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        conn.close()
        if count == 0:
            return
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"memory_{timestamp}.db"
        shutil.copy2(db_path, backup_path)
        # Rotate: keep only last 3
        backups = sorted(backup_dir.glob("memory_*.db"))
        for old in backups[:-3]:
            old.unlink()
    except (sqlite3.Error, OSError):
        pass  # Backup failure must never block container init


def _run_migrations_on_init(db_path: Path, migrations_dir: Path) -> None:
    """Run pending migrations on container initialization."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    config = DatabaseConfig(db_path=db_path)
    run_migrations(config, migrations_dir)


def override_database_for_testing(container: Container, test_db_path: Path) -> None:
    container.config.db_path.override(test_db_path)
    container.database_config.reset()


# =============================================================================
# Convenience Factory Functions (Canonical SSOT)
# =============================================================================

# Unified container cache — replaces per-module caching strategies
_container_cache: dict[str, Container] = {}
_container_lock = Lock()

# Global singleton instances for non-container services
_hook_service: HookService | None = None
_workflow_executor: WorkflowExecutor | None = None


def get_container(db_path: Path | None = None) -> Container:
    """Get or create cached container for the given db_path.

    Thread-safe. Replaces all per-module caching with single canonical cache.
    """
    cache_key = str(db_path or "default")
    if cache_key not in _container_cache:
        with _container_lock:
            if cache_key not in _container_cache:
                _container_cache[cache_key] = create_container(db_path)
    return _container_cache[cache_key]


def get_repository(db_path: Path | None = None) -> ObservationRepository:
    """Get the ObservationRepository instance."""
    return get_container(db_path).observation_repository()


def get_tmux_orchestrator() -> TmuxOrchestrator:
    """Get the singleton TmuxOrchestrator instance."""
    return get_container().tmux_orchestrator()


def get_memory_service(db_path: Path | None = None) -> MemoryService:
    """Get a MemoryService instance."""
    return get_container(db_path).memory_service()


def get_session_service(db_path: Path | None = None) -> SessionService:
    """Get a SessionService instance."""
    return get_container(db_path).session_service()


def get_sync_service(db_path: Path | None = None) -> SyncService:
    """Get a SyncService instance."""
    return get_container(db_path).sync_service()


def get_health_service(db_path: Path | None = None) -> HealthCheckService:
    """Get a HealthCheckService instance."""
    return get_container(db_path).health_check_service()


def get_health_check_service(db_path: Path | None = None) -> HealthCheckService:
    """Alias for get_health_service() — backward compat for CLI commands."""
    return get_health_service(db_path)


def get_hook_service() -> HookService:
    """Get the singleton HookService instance."""
    global _hook_service
    if _hook_service is None:
        _hook_service = HookService()
    return _hook_service


def get_promise_repository(db_path: Path | None = None) -> PromiseContractRepository:
    """Get the singleton PromiseContractRepository instance."""
    return get_container(db_path).promise_contract_repository()


def get_workspace_manager(db_path: Path | None = None) -> WorkspaceManager:
    """Get the WorkspaceManager instance via DI container."""
    return get_container(db_path).workspace_manager()


def get_workflow_executor() -> WorkflowExecutor:
    """Get the singleton WorkflowExecutor instance.

    Wires TmuxOrchestrator, MemoryService, WorkspaceManager, HookService.
    """
    global _workflow_executor
    if _workflow_executor is None:
        _workflow_executor = WorkflowExecutor(
            tmux_orchestrator=get_tmux_orchestrator(),
            memory_service=get_memory_service(),
            workspace_manager=get_workspace_manager(),
            hook_service=get_hook_service(),
        )
    return _workflow_executor


def get_telemetry_service(db_path: Path | None = None) -> TelemetryService:
    """Get a TelemetryService instance."""
    return get_container(db_path).telemetry_service()


def get_cleanup_service(db_path: Path | None = None) -> CleanupService:
    """Get a CleanupService instance."""
    return get_container(db_path).cleanup_service()


def get_scheduler_service(db_path: Path | None = None) -> SchedulerService:
    """Get a SchedulerService instance."""
    return get_container(db_path).scheduler_service()


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
    except (OSError, ValueError):
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


def get_message_store(db_path: Path | None = None) -> MessageStore:
    """Get the MessageStore instance."""
    return get_container(db_path).message_repository()


def get_agent_messenger(db_path: Path | None = None) -> AgentMessenger:
    """Get the AgentMessenger instance."""
    return get_container(db_path).agent_messenger()


def get_database_connection(db_path: Path | None = None) -> DatabaseConnection:
    """Get the DatabaseConnection instance."""
    return get_container(db_path).database_connection()
