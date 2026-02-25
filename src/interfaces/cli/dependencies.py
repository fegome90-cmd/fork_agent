"""CLI dependencies for dependency injection."""

from __future__ import annotations

from pathlib import Path

from src.application.services.memory_service import MemoryService
from src.application.services.orchestration.hook_service import HookService
from src.application.services.scheduler_service import SchedulerService
from src.application.services.cleanup_service import CleanupService
from src.infrastructure.persistence.container import Container, create_container
from src.infrastructure.persistence.health_check import HealthCheckService

_hook_service: HookService | None = None


def get_hook_service() -> HookService:
    """Get or create shared singleton HookService instance."""
    global _hook_service
    if _hook_service is None:
        _hook_service = HookService()
    return _hook_service


def get_container(db_path: Path | None = None) -> Container:
    return create_container(db_path)


def get_repository(db_path: Path | None = None):
    container = get_container(db_path)
    return container.observation_repository()


def get_memory_service(db_path: Path | None = None) -> MemoryService:
    """Get MemoryService instance for CLI commands."""
    container = get_container(db_path)
    return container.memory_service()


def get_scheduler_service(db_path: Path | None = None) -> SchedulerService:
    """Get SchedulerService instance for CLI commands."""
    container = get_container(db_path)
    return container.scheduler_service()


def get_cleanup_service(db_path: Path | None = None) -> CleanupService:
    """Get CleanupService instance for CLI commands."""
    container = get_container(db_path)
    return container.cleanup_service()


def get_health_check_service(db_path: Path | None = None) -> HealthCheckService:
    """Get HealthCheckService instance for CLI commands."""
    container = get_container(db_path)
    return container.health_check_service()
