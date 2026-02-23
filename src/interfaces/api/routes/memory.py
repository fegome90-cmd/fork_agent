"""Rutas para memoria."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import (
    Observation,
    ObservationCreate,
    ObservationListResponse,
    ObservationResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])


_observations: dict[str, Observation] = {}


@router.post("", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation(
    request: ObservationCreate,
    _: str = Depends(verify_api_key),
) -> ObservationResponse:
    """Guarda una observación."""
    obs_id = f"obs-{uuid.uuid4().hex[:6]}"
    observation = Observation(
        id=obs_id,
        content=request.content,
        created_at=datetime.now(),
    )
    _observations[obs_id] = observation
    return ObservationResponse(data=observation)


@router.get("", response_model=ObservationListResponse)
async def list_observations(_: str = Depends(verify_api_key)) -> ObservationListResponse:
    """Lista todas las observaciones."""
    return ObservationListResponse(data=list(_observations.values()))


@router.get("/search", response_model=ObservationListResponse)
async def search_observations(
    q: str = Query(..., description="Query de búsqueda"),
    _: str = Depends(verify_api_key),
) -> ObservationListResponse:
    """Busca observaciones."""
    results = [obs for obs in _observations.values() if q.lower() in obs.content.lower()]
    return ObservationListResponse(data=results)


@router.get("/{obs_id}", response_model=ObservationResponse)
async def get_observation(
    obs_id: str,
    _: str = Depends(verify_api_key),
) -> ObservationResponse:
    """Obtiene una observación por ID."""
    if obs_id not in _observations:
        raise HTTPException(status_code=404, detail="Observation not found")
    return ObservationResponse(data=_observations[obs_id])


@router.delete("/{obs_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_observation(
    obs_id: str,
    _: str = Depends(verify_api_key),
) -> None:
    """Elimina una observación."""
    if obs_id not in _observations:
        raise HTTPException(status_code=404, detail="Observation not found")
    del _observations[obs_id]
