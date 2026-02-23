"""Rutas para workflow."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import (
    WorkflowPlanRequest,
    WorkflowResponse,
)

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/outline", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: WorkflowPlanRequest,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Crea un nuevo plan de workflow."""
    plan_id = f"plan-{uuid.uuid4().hex[:6]}"
    data = {
        "plan_id": plan_id,
        "task": request.task,
        "status": "created",
        "created_at": datetime.now(),
    }
    return WorkflowResponse(data=data)


@router.post("/{plan_id}/execute", response_model=WorkflowResponse)
async def execute_plan(
    plan_id: str,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Ejecuta un plan."""
    execute_id = f"exec-{uuid.uuid4().hex[:6]}"
    data = {
        "execute_id": execute_id,
        "plan_id": plan_id,
        "status": "running",
        "started_at": datetime.now(),
    }
    return WorkflowResponse(data=data)


@router.post("/{plan_id}/verify", response_model=WorkflowResponse)
async def verify_plan(
    _plan_id: str,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Verifica un plan."""
    verify_id = f"verify-{uuid.uuid4().hex[:3]}"
    data = {
        "verify_id": verify_id,
        "execute_id": f"exec-{uuid.uuid4().hex[:6]}",
        "status": "passed",
        "tests": {"total": 50, "passed": 50, "failed": 0},
        "coverage": 95.2,
    }
    return WorkflowResponse(data=data)


@router.post("/{plan_id}/ship", response_model=WorkflowResponse)
async def ship_plan(
    plan_id: str,
    request: dict,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Hace ship de un plan."""
    data = {
        "plan_id": plan_id,
        "branch": request.get("branch", "main"),
        "commit_message": request.get("commit_message", ""),
        "status": "shipped",
    }
    return WorkflowResponse(data=data)


@router.get("/{plan_id}/status", response_model=WorkflowResponse)
async def get_plan_status(
    plan_id: str,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Obtiene el estado de un plan."""
    data = {
        "plan_id": plan_id,
        "status": "pending",
        "created_at": datetime.now(),
    }
    return WorkflowResponse(data=data)
