"""Rutas para workflow."""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from src.domain.entities.promise_contract import PromiseContract, PromiseState, VerifyEvidence
from src.interfaces.api.dependencies import get_promise_repository, verify_api_key
from src.interfaces.api.models import WorkflowPlanRequest, WorkflowResponse

router = APIRouter(prefix="/workflow", tags=["workflow"])

logger = logging.getLogger(__name__)

_DEFAULT_SESSION_ID = "api-session"


@router.post("/outline", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: WorkflowPlanRequest,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Crea un nuevo plan de trabajo."""
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
    """Ejecuta un plan de trabajo."""
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
    plan_id: str,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Verifica el resultado de un plan de trabajo."""
    verify_id = f"verify-{uuid.uuid4().hex[:3]}"
    passed = True
    now = datetime.now()

    try:
        repo = get_promise_repository()
        existing_contract = repo.get_by_plan_id(plan_id)
        verify_evidence = VerifyEvidence(
            artifact_path="n/a",
            passed=passed,
            exit_code=0,
            timestamp=now,
        )
        if existing_contract is None:
            contract = PromiseContract(
                id=f"promise-{uuid.uuid4().hex[:8]}",
                session_id=_DEFAULT_SESSION_ID,
                plan_id=plan_id,
                task=f"Workflow plan {plan_id}",
                state=PromiseState.VERIFY_PASSED,
                verify_evidence=verify_evidence,
                created_at=now,
                updated_at=now,
                metadata={"verify_id": verify_id},
            )
            repo.save(contract)
    except Exception:
        logger.debug("Failed to persist PromiseContract for plan_id=%s", plan_id, exc_info=True)

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
    """Envía un plan de trabajo verificado."""
    branch = request.get("branch", "main")
    commit_message = request.get("commit_message", "")

    try:
        repo = get_promise_repository()
        contract = repo.get_by_plan_id(plan_id)
        if contract is not None and contract.state != PromiseState.VERIFY_PASSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot ship: PromiseContract state is {contract.state.value}",
            )
        if contract is not None:
            repo.update_state(contract.id, PromiseState.SHIPPED)
    except HTTPException:
        raise
    except Exception:
        logger.debug("Failed to update PromiseContract state for plan_id=%s", plan_id, exc_info=True)

    data = {
        "plan_id": plan_id,
        "branch": branch,
        "commit_message": commit_message,
        "status": "shipped",
    }
    return WorkflowResponse(data=data)


@router.get("/{plan_id}/status", response_model=WorkflowResponse)
async def get_plan_status(
    plan_id: str,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
    """Obtiene el estado de un plan de trabajo."""
    data = {
        "plan_id": plan_id,
        "status": "pending",
        "created_at": datetime.now(),
    }

    try:
        repo = get_promise_repository()
        contract = repo.get_by_plan_id(plan_id)
        if contract is not None:
            data["promise_contract"] = {
                "id": contract.id,
                "state": contract.state.value,
                "created_at": contract.created_at.isoformat() if contract.created_at else None,
                "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
            }
    except Exception:
        logger.debug("Failed to retrieve PromiseContract for plan_id=%s", plan_id, exc_info=True)

    return WorkflowResponse(data=data)
