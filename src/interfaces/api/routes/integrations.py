"""Routes for external integrations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.infrastructure.external_apis.branch_review_client import (
    BranchReviewClient,
    BranchReviewError,
)
from src.interfaces.api.dependencies import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_branch_review_client() -> BranchReviewClient:
    """Get branch-review client instance."""
    return BranchReviewClient()


# --- Branch Review Integration ---

@router.get("/branch-review/info")
async def get_branch_review_info(
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Get branch-review API metadata.

    This is a passthrough to the branch-review /api/review/info endpoint.
    """
    try:
        with get_branch_review_client() as client:
            return {"data": client.get_info(), "error": None}
    except Exception as e:
        logger.error(f"Failed to get branch-review info: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"branch-review API unavailable: {e}",
        ) from e


@router.get("/branch-review/run")
async def get_branch_review_run(
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Get current branch-review run status."""
    try:
        with get_branch_review_client() as client:
            return {"data": client.get_run(), "error": None}
    except BranchReviewError as e:
        return {"data": None, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        logger.error(f"Failed to get branch-review run: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"branch-review API unavailable: {e}",
        ) from e


@router.get("/branch-review/final/{run_id}")
async def get_branch_review_final(
    run_id: str,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Get final verdict for a branch-review run."""
    try:
        with get_branch_review_client() as client:
            return {"data": client.get_final(run_id), "error": None}
    except BranchReviewError as e:
        return {"data": None, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        logger.error(f"Failed to get branch-review final: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"branch-review API unavailable: {e}",
        ) from e


class BranchReviewCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=50)
    args: dict | None = None
    model_config = {"extra": "forbid"}


class BranchReviewWorkflowRequest(BaseModel):
    agents: list[str] | None = None
    model_config = {"extra": "forbid"}


@router.post("/branch-review/command")
async def execute_branch_review_command(
    request: BranchReviewCommandRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Execute a branch-review command.

    Commands: init, explore, plan, run, ingest, verdict, merge, cleanup
    """
    command = request.command
    args = request.args or {}

    try:
        with get_branch_review_client() as client:
            result = client.execute_command(command, args)
            return {"data": result, "error": None}
    except BranchReviewError as e:
        return {"data": None, "error": {"code": e.code, "message": e.message}}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.error(f"Failed to execute branch-review command: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"branch-review API unavailable: {e}",
        ) from e


@router.post("/branch-review/workflow")
async def run_branch_review_workflow(
    request: BranchReviewWorkflowRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Run a complete branch-review workflow.

    Optional body: {"agents": ["code-reviewer", "code-simplifier"]}
    """
    agents = request.agents or ["code-reviewer"]

    try:
        with get_branch_review_client() as client:
            result = client.run_full_review(agents=agents)
            return {"data": result, "error": None}
    except BranchReviewError as e:
        return {"data": None, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        logger.error(f"Failed to run branch-review workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"branch-review API unavailable: {e}",
        ) from e
