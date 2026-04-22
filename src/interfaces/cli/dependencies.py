"""CLI dependencies — re-exports from canonical container.

This module exists so CLI commands can import from a CLI-local path,
keeping the interface layer clean. All actual DI logic lives in
src.infrastructure.persistence.container.
"""

from __future__ import annotations

from src.infrastructure.persistence.container import (  # noqa: F401
    get_cleanup_service,
    get_health_check_service,
    get_hook_service,
    get_memory_service,
    get_scheduler_service,
    get_telemetry_service,
)


# Lazy imports for heavy dependencies — only loaded when accessed.
# Avoids pulling dependency_injector (~128ms) into the CLI hot path.
def __getattr__(name: str):
    """Lazy re-exports that avoid triggering dependency_injector import."""
    _lazy = {
        "Container",
        "create_container",
        "detect_memory_db_path",
        "get_container",
        "get_memory_service_auto",
        "get_promise_repository",
        "get_repository",
        "get_session_service",
        "get_sync_service",
        "get_tmux_orchestrator",
        "get_workflow_executor",
        "get_workspace_manager",
        "override_database_for_testing",
    }
    if name in _lazy:
        from src.infrastructure.persistence import container as _c

        return getattr(_c, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
