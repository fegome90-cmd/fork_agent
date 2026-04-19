"""CLI dependencies — re-exports from canonical container.

This module exists so CLI commands can import from a CLI-local path,
keeping the interface layer clean. All actual DI logic lives in
src.infrastructure.persistence.container.
"""

from __future__ import annotations

from src.infrastructure.persistence.container import (  # noqa: F401
    Container,
    create_container,
    detect_memory_db_path,
    get_cleanup_service,
    get_container,
    get_health_check_service,
    get_hook_service,
    get_memory_service,
    get_memory_service_auto,
    get_promise_repository,
    get_repository,
    get_scheduler_service,
    get_session_service,
    get_sync_service,
    get_telemetry_service,
    get_tmux_orchestrator,
    get_workflow_executor,
    get_workspace_manager,
    override_database_for_testing,
)
