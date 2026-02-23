"""Rutas para agentes."""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import (
    AgentSession,
    AgentSessionCreate,
    AgentSessionResponse,
    SessionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/sessions", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: AgentSessionCreate,
    _: str = Depends(verify_api_key),
) -> AgentSessionResponse:
    logger.info(f"Creating agent session: agent_type={request.agent_type}")
    session_id = f"fork-{request.agent_type}-{uuid.uuid4().hex[:12]}"
    tmux_session = None

    if request.tmux:
        tmux_session = f"fork-{request.agent_type}-{uuid.uuid4().hex[:12]}"

    hooks = []
    if request.hooks:
        hooks = [
            {"type": "workspace-init", "status": "pending"},
            {"type": "tmux-session-per-agent", "status": "pending"},
        ]

    session = AgentSession(
        session_id=session_id,
        agent_type=request.agent_type,
        status="starting",
        started_at=datetime.now(),
        tmux_session=tmux_session,
        hooks=hooks,
    )

    logger.info(f"Agent session created: session_id={session_id}")
    return AgentSessionResponse(data=session)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(_: str = Depends(verify_api_key)) -> SessionListResponse:
    logger.info("Listing agent sessions")
    return SessionListResponse(data=[])


@router.get("/sessions/{session_id}", response_model=AgentSessionResponse)
async def get_session(
    session_id: str,
    _: str = Depends(verify_api_key),
) -> AgentSessionResponse:
    logger.info(f"Getting session: session_id={session_id}")
    raise HTTPException(status_code=404, detail="Session not found")


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    _: str = Depends(verify_api_key),
) -> None:
    logger.info(f"Delete session requested: session_id={session_id}")
