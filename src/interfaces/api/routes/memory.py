"""Memory routes for the API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.interfaces.api.dependencies import get_memory_service, verify_api_key
from src.interfaces.api.models import (
    Observation,
    ObservationCreate,
    ObservationListResponse,
    ObservationResponse,
    QueryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation(
    request: ObservationCreate,
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> ObservationResponse:
    """Save an observation."""
    try:
        observation = memory.save(content=request.content)
        return ObservationResponse(
            data=Observation(
                id=observation.id,
                content=observation.content,
                timestamp=observation.timestamp,
                metadata=observation.metadata,
                idempotency_key=observation.idempotency_key,
            )
        )
    except Exception as e:
        logger.error(f"Failed to create observation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save observation: {e}",
        ) from None


@router.get("", response_model=ObservationListResponse)
async def list_observations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> ObservationListResponse:
    """List recent observations."""
    try:
        observations = memory.get_recent(limit=limit, offset=offset)
        return ObservationListResponse(
            data=[
                Observation(
                    id=obs.id,
                    content=obs.content,
                    timestamp=obs.timestamp,
                    metadata=obs.metadata,
                    idempotency_key=obs.idempotency_key,
                )
                for obs in observations
            ],
            count=len(observations),
        )
    except Exception as e:
        logger.error(f"Failed to list observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list observations: {e}",
        ) from None


@router.get("/search", response_model=ObservationListResponse)
async def search_observations(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> ObservationListResponse:
    """Search observations using FTS5."""
    try:
        results = memory.search(q, limit=limit)
        return ObservationListResponse(
            data=[
                Observation(
                    id=obs.id,
                    content=obs.content,
                    timestamp=obs.timestamp,
                    metadata=obs.metadata,
                    idempotency_key=obs.idempotency_key,
                )
                for obs in results
            ],
            count=len(results),
        )
    except Exception as e:
        logger.error(f"Failed to search observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e}",
        ) from None


@router.get("/query", response_model=QueryResponse)
async def query_memory(
    agent: str | None = Query(None, description="Filter by agent ID"),
    run: str | None = Query(None, description="Filter by run ID"),
    event_type: str | None = Query(None, alias="event-type", description="Filter by event type"),
    limit: int = Query(20, ge=1, le=100),
    scan_limit: int = Query(1000, alias="scan-limit", description="Max observations to scan"),
    since: str | None = Query(None, description="Time filter (e.g., '24h', '7d', or ISO date)"),
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> QueryResponse:
    """Query memory events with structured filters."""
    # Parse since parameter to ms
    since_ms = None
    if since:
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        if since.endswith("h"):
            try:
                hours = int(since[:-1])
                since_ms = int((now - timedelta(hours=hours)).timestamp() * 1000)
            except ValueError:
                pass
        elif since.endswith("d"):
            try:
                days = int(since[:-1])
                since_ms = int((now - timedelta(days=days)).timestamp() * 1000)
            except ValueError:
                pass
        else:
            try:
                dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                since_ms = int(dt.timestamp() * 1000)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid --since format: {since}",
                ) from None

    try:
        results = memory.query(
            agent=agent,
            run_id=run,
            event_type=event_type,
            limit=limit,
            scan_limit=scan_limit,
            since_ms=since_ms,
        )

        # Map to structured output
        output = []
        for obs in results:
            output.append(
                {
                    "id": obs.id,
                    "timestamp": obs.timestamp,
                    "event_type": obs.metadata.get("event_type") if obs.metadata else None,
                    "run_id": obs.metadata.get("run_id") if obs.metadata else None,
                    "task_id": obs.metadata.get("task_id") if obs.metadata else None,
                    "agent_id": obs.metadata.get("agent_id") if obs.metadata else None,
                    "content": obs.content,
                    "metadata": obs.metadata,
                }
            )

        return QueryResponse(data=output, count=len(output))
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {e}",
        ) from None


@router.get("/timeline/{run_id}", response_model=QueryResponse)
async def get_timeline(
    run_id: str,
    scan_limit: int = Query(1000, alias="scan-limit"),
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> QueryResponse:
    """Get chronological timeline for a specific run."""
    try:
        # Use query with run_id and high limit
        results = memory.query(
            run_id=run_id,
            limit=scan_limit,
            scan_limit=scan_limit,
        )

        # Sort by timestamp ASC (chronological)
        results.sort(key=lambda o: o.timestamp)

        output = []
        for obs in results:
            output.append(
                {
                    "id": obs.id,
                    "timestamp": obs.timestamp,
                    "event_type": obs.metadata.get("event_type") if obs.metadata else None,
                    "agent_id": obs.metadata.get("agent_id") if obs.metadata else None,
                    "task_id": obs.metadata.get("task_id") if obs.metadata else None,
                    "content": obs.content,
                    "success": obs.metadata.get("success") if obs.metadata else None,
                }
            )

        return QueryResponse(data=output, count=len(output))
    except Exception as e:
        logger.error(f"Timeline failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Timeline failed: {e}",
        ) from None


@router.get("/{obs_id}", response_model=ObservationResponse)
async def get_observation(
    obs_id: str,
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> ObservationResponse:
    """Get an observation by ID."""
    try:
        observation = memory.get_by_id(obs_id)
        if not observation:
            raise HTTPException(status_code=404, detail="Observation not found")
        return ObservationResponse(
            data=Observation(
                id=observation.id,
                content=observation.content,
                timestamp=observation.timestamp,
                metadata=observation.metadata,
                idempotency_key=observation.idempotency_key,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get observation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving observation: {e}",
        ) from None


@router.delete("/{obs_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_observation(
    obs_id: str,
    _: str = Depends(verify_api_key),
    memory=Depends(get_memory_service),
) -> None:
    """Delete an observation."""
    try:
        observation = memory.get_by_id(obs_id)
        if not observation:
            raise HTTPException(status_code=404, detail="Observation not found")
        memory.delete(obs_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete observation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting observation: {e}",
        ) from None
