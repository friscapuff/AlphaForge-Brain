"""Sweep status API endpoints."""

from __future__ import annotations

from api.models.sweeps import SweepStatusModel
from fastapi import APIRouter, HTTPException
from services.sweeps import get_sweep_status

router = APIRouter(prefix="/api/v1/sweeps", tags=["sweeps"])


@router.get("/{sweep_id}", response_model=SweepStatusModel)
async def read_sweep_status(sweep_id: str) -> SweepStatusModel:
    """Return status and lineage details for the requested sweep."""

    try:
        payload = get_sweep_status(sweep_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sweep not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SweepStatusModel.model_validate(payload)
