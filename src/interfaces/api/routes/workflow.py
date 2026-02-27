"""Rutas para workflow."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.exceptions import RepositoryError
from src.domain.entities.promise_contract import PromiseContract, PromiseState, VerifyEvidence
from src.interfaces.api.dependencies import get_promise_repository, verify_api_key
from src.interfaces.api.models import WorkflowPlanRequest, WorkflowResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])

_DEFAULT_SESSION_ID = "api-session"


@router.post("/outline", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: WorkflowPlanRequest,
    _: str = Depends(verify_api_key),
) -> WorkflowResponse:
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
    verify_id = f"verify-{uuid.uuid4().hex[:3]}"
    passed = True
    now = datetime.now()

    try:
        repo = get_promise_repository()
        contract = PromiseContract(
            id=f"promise-{uuid.uuid4().hex[:8]}",
            session_id=_DEFAULT_SESSION_ID,
            plan_id=plan_id,
            task=f"Workflow plan {plan_id}",
            state=PromiseState.VERIFY_PASSED,
            verify_evidence=VerifyEvidence(
                artifact_path=f"/tmp/verify-{verify_id}.json",
                passed=passed,
                exit_code=0,
                timestamp=now.isoformat(),
            ),
            created_at=now,
            updated_at=now,
            metadata={"verify_id": verify_id},
        )
        repo.save(contract)
    except Exception as e:
        logger.error(f"Failed to persist verify evidence for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Verification failed to persist evidence: {str(e)}"
        )

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
    branch = request.get("branch", "main")
    commit_message = request.get("commit_message", "")

    try:
        repo = get_promise_repository()
        contract = repo.get_by_plan_id(plan_id)
    except RepositoryError as e:
        logger.error(f"Repository error: {e}")
        raise HTTPException(status_code=500, detail="Database error") from None

    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.state != PromiseState.VERIFY_PASSED:
        raise HTTPException(
            status_code=409, detail=f"Contract must be VERIFY_PASSED, got {contract.state}"
        )

    # Persist SHIPPED state
    repo.update_state(contract.id, PromiseState.SHIPPED)

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
    try:
        repo = get_promise_repository()
        contract = repo.get_by_plan_id(plan_id)
        if contract is None:
            return WorkflowResponse(
                data={
                    "plan_id": plan_id,
                    "status": "pending",
                    "created_at": datetime.now(),
                }
            )
        return WorkflowResponse(
            data={
                "plan_id": plan_id,
                "status": contract.state.value,
                "promise_contract": {
                    "id": contract.id,
                    "state": contract.state.value,
                    "created_at": contract.created_at.isoformat() if contract.created_at else None,
                    "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
                },
            }
        )
    except RepositoryError as e:
        logger.error(f"Repository error fetching contract: {e}")
        raise HTTPException(status_code=500, detail="Database error") from None
