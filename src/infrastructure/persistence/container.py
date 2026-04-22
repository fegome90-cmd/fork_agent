"""Dependency injection container for persistence layer.

Fast path: get_memory_service(), get_telemetry_service(), get_repository()
bypass the DI container entirely for common CLI operations, saving ~140ms
of startup time by avoiding dependency_injector/fastapi import chains.

The Container class and create_container() live in _container_di.py and are
only loaded when advanced DI features (get_container, sync, session, etc.)
are needed.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock

# Fast-path imports only — these are lightweight (~69ms total)
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.persistence.repositories.sync_repository import (
    SyncRepositoryImpl,
)
from src.infrastructure.persistence.repositories.telemetry_repository import (
    TelemetryRepositoryImpl,
)

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _auto_backup(db_path: Path) -> None:
    """Auto-backup DB before container init if DB exists and has data."""
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
        backups = sorted(backup_dir.glob("memory_*.db"))
        for old in backups[:-3]:
            old.unlink()
    except (sqlite3.Error, OSError):
        pass


def _run_migrations_on_init(db_path: Path, migrations_dir: Path) -> None:
    """Run pending migrations on container initialization."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    config = DatabaseConfig(db_path=db_path)
    run_migrations(config, migrations_dir)


# ---------------------------------------------------------------------------
# Fast path: bypass dependency_injector for common CLI operations
# ---------------------------------------------------------------------------

_fast_cache: dict[str, tuple[ObservationRepository, TelemetryRepositoryImpl]] = {}
_fast_lock = Lock()


def _get_or_create_fast(
    db_path: Path | None = None,
) -> tuple[ObservationRepository, TelemetryRepositoryImpl]:
    """Create repository instances without the DI container."""
    resolved = db_path or DEFAULT_DB_PATH
    cache_key = str(resolved)
    if cache_key in _fast_cache:
        return _fast_cache[cache_key]
    with _fast_lock:
        if cache_key in _fast_cache:
            return _fast_cache[cache_key]
        resolved.parent.mkdir(parents=True, exist_ok=True)
        _auto_backup(resolved)
        _run_migrations_on_init(resolved, DEFAULT_MIGRATIONS_DIR)
        config = DatabaseConfig(db_path=resolved)
        conn = DatabaseConnection(config=config)
        sync_repo = SyncRepositoryImpl(connection=conn)
        repo = ObservationRepository(connection=conn, sync_repo=sync_repo)
        telemetry_repo = TelemetryRepositoryImpl(connection=conn)
        _fast_cache[cache_key] = (repo, telemetry_repo)
        return repo, telemetry_repo


# ---------------------------------------------------------------------------
# Convenience Factory Functions (Canonical SSOT)
# ---------------------------------------------------------------------------

_container_cache: dict[str, object] = {}
_container_lock = Lock()

# Global singleton instances for non-container services
_hook_service: object | None = None
_workflow_executor: object | None = None


# Reference to create_container — can be patched in tests.
# At runtime, lazily resolves to the real implementation.
_create_container_ref = None


def _get_create_container():
    """Resolve create_container lazily (patchable for tests)."""
    global _create_container_ref
    if _create_container_ref is None:
        from src.infrastructure.persistence._container_di import create_container

        _create_container_ref = create_container
    return _create_container_ref


# Alias for backward-compat patching: tests do
#   patch("src.infrastructure.persistence.container.create_container", ...)
# This works because __getattr__ resolves it.
def create_container(db_path=None, export_dir=None):
    """Create a DI container (lazy-loaded, patchable for tests)."""
    return _get_create_container()(db_path, export_dir)


def get_container(db_path: Path | None = None):
    """Get or create cached DI container (lazy-loads dependency_injector)."""
    cache_key = str(db_path or "default")
    if cache_key not in _container_cache:
        with _container_lock:
            if cache_key not in _container_cache:
                _container_cache[cache_key] = create_container(db_path)
    return _container_cache[cache_key]


def get_repository(db_path: Path | None = None) -> ObservationRepository:
    """Get the ObservationRepository instance (fast path)."""
    repo, _ = _get_or_create_fast(db_path)
    return repo


def get_memory_service(db_path: Path | None = None):
    """Get a MemoryService instance (fast path)."""
    from src.application.services.memory_service import MemoryService
    from src.application.services.telemetry.telemetry_service import TelemetryService

    repo, telemetry_repo = _get_or_create_fast(db_path)
    telemetry_svc = TelemetryService(repository=telemetry_repo)
    return MemoryService(repository=repo, telemetry_service=telemetry_svc)


def get_telemetry_service(db_path: Path | None = None):
    """Get a TelemetryService instance (fast path)."""
    from src.application.services.telemetry.telemetry_service import TelemetryService

    _, telemetry_repo = _get_or_create_fast(db_path)
    return TelemetryService(repository=telemetry_repo)


def get_hook_service():
    """Get the singleton HookService instance (no DI container needed)."""
    global _hook_service
    if _hook_service is None:
        from src.application.services.orchestration.hook_service import HookService

        _hook_service = HookService()
    return _hook_service


# ---------------------------------------------------------------------------
# DI-container-dependent functions (lazy-load dependency_injector)
# ---------------------------------------------------------------------------


def get_tmux_orchestrator():
    """Get the singleton TmuxOrchestrator instance."""
    return get_container().tmux_orchestrator()


def get_session_service(db_path: Path | None = None):
    """Get a SessionService instance."""
    return get_container(db_path).session_service()


def get_sync_service(db_path: Path | None = None):
    """Get a SyncService instance."""
    return get_container(db_path).sync_service()


def get_health_service(db_path: Path | None = None):
    """Get a HealthCheckService instance."""
    return get_container(db_path).health_check_service()


def get_health_check_service(db_path: Path | None = None):
    """Alias for get_health_service() — backward compat for CLI commands."""
    return get_health_service(db_path)


def get_promise_repository(db_path: Path | None = None):
    """Get the singleton PromiseContractRepository instance."""
    return get_container(db_path).promise_contract_repository()


def get_workspace_manager(db_path: Path | None = None):
    """Get the WorkspaceManager instance via DI container."""
    return get_container(db_path).workspace_manager()


def get_workflow_executor():
    """Get the singleton WorkflowExecutor instance."""
    global _workflow_executor
    if _workflow_executor is None:
        from src.application.services.workflow.executor import WorkflowExecutor

        _workflow_executor = WorkflowExecutor(
            tmux_orchestrator=get_tmux_orchestrator(),
            memory_service=get_memory_service(),
            workspace_manager=get_workspace_manager(),
            hook_service=get_hook_service(),
        )
    return _workflow_executor


def get_cleanup_service(db_path: Path | None = None):
    """Get a CleanupService instance."""
    return get_container(db_path).cleanup_service()


def get_scheduler_service(db_path: Path | None = None):
    """Get a SchedulerService instance."""
    return get_container(db_path).scheduler_service()


def detect_memory_db_path() -> Path:
    """Detect the appropriate memory DB path based on current workspace."""
    try:
        workspace_manager = get_workspace_manager()
        workspace = workspace_manager.detect_workspace()
        if workspace is not None:
            worktree_db_dir = workspace.path / ".memory"
            worktree_db_dir.mkdir(parents=True, exist_ok=True)
            return worktree_db_dir / "observations.db"
    except (OSError, ValueError):
        pass
    return DEFAULT_DB_PATH


def get_memory_service_auto():
    """Get MemoryService with automatic workspace-aware DB path detection."""
    db_path = detect_memory_db_path()
    return get_memory_service(db_path)


def get_message_store(db_path: Path | None = None):
    """Get the MessageStore instance."""
    return get_container(db_path).message_repository()


def get_agent_messenger(db_path: Path | None = None):
    """Get the AgentMessenger instance."""
    return get_container(db_path).agent_messenger()


def get_database_connection(db_path: Path | None = None) -> DatabaseConnection:
    """Get the DatabaseConnection instance."""
    return get_container(db_path).database_connection()


# ---------------------------------------------------------------------------
# Re-exports for backward compat (Container class, create_container, etc.)
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> object:
    """Lazy-load Container class and related symbols from _container_di."""
    if name in ("Container", "create_container", "override_database_for_testing"):
        from src.infrastructure.persistence import _container_di

        return getattr(_container_di, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
