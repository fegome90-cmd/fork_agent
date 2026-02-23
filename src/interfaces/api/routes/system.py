"""Rutas del sistema."""

import logging
import time

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import HealthResponse, MetricsResponse
from src.interfaces.api.services.pm2_service import pm2_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

_start_time = time.time()
_request_count = 0
_error_count = 0


def increment_requests() -> None:
    global _request_count
    _request_count += 1


def increment_errors() -> None:
    global _error_count
    _error_count += 1


@router.get("/health", response_model=HealthResponse)
async def health_check(_: str = Depends(verify_api_key)) -> HealthResponse:
    logger.info("Health check requested")
    pm2_status = await pm2_service.get_status()
    return HealthResponse(
        status="healthy",
        pm2=pm2_status,
        version="1.0.0",
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(_: str = Depends(verify_api_key)) -> MetricsResponse:
    logger.info("Metrics requested")
    uptime = int(time.time() - _start_time)
    return MetricsResponse(
        cpu=0.0,
        memory="0MB",
        uptime=uptime,
        requests_total=_request_count,
        errors_total=_error_count,
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
