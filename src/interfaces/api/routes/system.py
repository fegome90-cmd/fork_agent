"""Rutas del sistema."""

import logging
import threading
import time

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from src.infrastructure.agent_backends import get_available_backends, list_all_backends
from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import AgentInfo, HealthResponse, MetricsResponse
from src.interfaces.api.services.pm2_service import pm2_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

_start_time = time.time()
_request_count = 0
_error_count = 0
_counters_lock = threading.Lock()  # BUG FIX: Thread-safe counters


def increment_requests() -> None:
    """BUG FIX: Thread-safe request counter increment."""
    global _request_count
    with _counters_lock:
        _request_count += 1


def increment_errors() -> None:
    """BUG FIX: Thread-safe error counter increment."""
    global _error_count
    with _counters_lock:
        _error_count += 1


@router.get("/health", response_model=HealthResponse)
async def health_check(_: str = Depends(verify_api_key)) -> HealthResponse:
    """Health check with agent backend status.

    Returns information about available agent backends and their installation status.
    """
    logger.info("Health check requested")
    pm2_status = await pm2_service.get_status()

    # Get agent backend information (O(n) instead of O(n*m))
    available_backends = get_available_backends()
    all_backends = list_all_backends()
    available_map = {b.name: b for b in available_backends}

    agents: list[AgentInfo] = [
        AgentInfo(
            name=backend_name,
            display_name=backend.display_name if backend else backend_name,
            available=backend is not None,
        )
        for backend_name in all_backends
        if (backend := available_map.get(backend_name)) or True
    ]

    # Determine overall health status
    has_available_agents = len(available_backends) > 0
    overall_status = "healthy" if has_available_agents else "degraded"

    return HealthResponse(
        status=overall_status,
        pm2=pm2_status,
        agents=agents,
        version="1.0.0",
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(_: str = Depends(verify_api_key)) -> MetricsResponse:
    """Get system metrics.

    NOTE: CPU and memory metrics are stubs returning placeholder values.
    Real implementation would require psutil or similar library.
    """
    logger.info("Metrics requested")
    uptime = int(time.time() - _start_time)
    with _counters_lock:  # BUG FIX: Thread-safe read
        request_count = _request_count
        error_count = _error_count
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_used = f"{memory.used // (1024 * 1024)}MB"
        memory_total = f"{memory.total // (1024 * 1024)}MB"
    except ImportError:
        cpu_percent = 0.0
        memory_used = "0MB"
        memory_total = "0MB"

    return MetricsResponse(
        cpu=cpu_percent,
        memory=memory_used,
        memory_total=memory_total,
        uptime=uptime,
        requests_total=request_count,
        errors_total=error_count,
    )


@router.get("/logs", response_class=PlainTextResponse)
async def get_logs(
    pm_id: int | None = Query(None, description="PM2 process ID"),
    lines: int = Query(100, ge=1, le=1000, description="Number of lines"),
    _: str = Depends(verify_api_key),
) -> str:
    logger.info(f"Logs requested for pm_id={pm_id}, lines={lines}")
    return await pm2_service.get_logs(pm_id, lines)


@router.get("/logs/{pm_id}", response_class=PlainTextResponse)
async def get_process_logs(
    pm_id: int,
    lines: int = Query(100, ge=1, le=1000),
    _: str = Depends(verify_api_key),
) -> str:
    logger.info(f"Process logs requested for pm_id={pm_id}")
    return await pm2_service.get_logs(pm_id, lines)
