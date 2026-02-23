"""Rutas para procesos."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import (
    ProcessListResponse,
    ProcessResponse,
    ProcessScaleRequest,
    ProcessStartRequest,
)
from src.interfaces.api.services.pm2_service import pm2_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("", response_model=ProcessListResponse)
async def list_processes(_: str = Depends(verify_api_key)) -> ProcessListResponse:
    logger.info("Listing all processes")
    processes = await pm2_service.list_processes()
    return ProcessListResponse(
        data=processes,
        meta={"total": len(processes), "version": "1.0.0"},
    )


@router.get("/{pm_id}", response_model=ProcessListResponse)
async def get_process(pm_id: int, _: str = Depends(verify_api_key)) -> ProcessListResponse:
    logger.info(f"Getting process: pm_id={pm_id}")
    process = await pm2_service.get_process(pm_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return ProcessListResponse(data=[process], meta={"total": 1, "version": "1.0.0"})


@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def start_process(
    request: ProcessStartRequest,
    _: str = Depends(verify_api_key),
) -> ProcessResponse:
    logger.info(f"Starting process: name={request.name}")
    result = await pm2_service.start_process(
        name=request.name,
        script=request.script,
        args=request.args,
        cwd=request.cwd,
        env=request.env,
    )
    return ProcessResponse(data=result)


@router.post("/{pm_id}/stop", response_model=ProcessResponse)
async def stop_process(pm_id: int, _: str = Depends(verify_api_key)) -> ProcessResponse:
    logger.info(f"Stopping process: pm_id={pm_id}")
    result = await pm2_service.stop_process(pm_id)
    return ProcessResponse(data=result)


@router.post("/{pm_id}/restart", response_model=ProcessResponse)
async def restart_process(pm_id: int, _: str = Depends(verify_api_key)) -> ProcessResponse:
    logger.info(f"Restarting process: pm_id={pm_id}")
    result = await pm2_service.restart_process(pm_id)
    return ProcessResponse(data=result)


@router.delete("/{pm_id}", response_model=ProcessResponse)
async def delete_process(pm_id: int, _: str = Depends(verify_api_key)) -> ProcessResponse:
    logger.info(f"Deleting process: pm_id={pm_id}")
    result = await pm2_service.delete_process(pm_id)
    return ProcessResponse(data=result)


@router.post("/{pm_id}/scale", response_model=ProcessResponse)
async def scale_process(
    pm_id: int,
    request: ProcessScaleRequest,
    _: str = Depends(verify_api_key),
) -> ProcessResponse:
    logger.info(f"Scaling process: pm_id={pm_id}, instances={request.instances}")
    result = await pm2_service.scale_process(pm_id, request.instances)
    return ProcessResponse(data=result)
