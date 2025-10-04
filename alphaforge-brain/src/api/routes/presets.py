"""Preset API routes.

FastAPI dependency injection with Depends(...) triggers ruff B008; suppress for this file.
"""

# ruff: noqa: B008
from __future__ import annotations

from typing import Any

from domain.presets.service import PresetService, get_preset_service
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=["presets"])  # root


# In-memory store; future task T057 will replace with persistent service
def svc_dep() -> PresetService:
    # Always resolve dynamically to pick up test env var isolation
    return get_preset_service()


class PresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    config: dict[str, Any]


class PresetResponse(BaseModel):
    preset_id: str
    name: str
    config: dict[str, Any]


class PresetList(BaseModel):
    items: list[PresetResponse]


@router.post("/presets", response_model=PresetResponse)
async def create_preset(
    req: PresetCreate, svc: PresetService = Depends(svc_dep)
) -> PresetResponse:
    preset_id, created = svc.create(req.name, req.config)
    # If not created treat as conflict (same name+config) but idempotent return
    if not created:
        # Could raise 409; we choose idempotent success for determinism
        pass
    rec = svc.get(preset_id)
    assert rec is not None  # safety
    return PresetResponse(preset_id=preset_id, name=rec["name"], config=rec["config"])


@router.get("/presets", response_model=PresetList)
async def list_presets(
    svc: PresetService = Depends(svc_dep),
) -> PresetList:
    items = []
    for rec in svc.list():
        items.append(
            PresetResponse(
                preset_id=rec["preset_id"], name=rec["name"], config=rec["config"]
            )
        )
    return PresetList(items=items)


@router.get("/presets/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: str, svc: PresetService = Depends(svc_dep)
) -> PresetResponse:
    rec = svc.get(preset_id)
    if not rec:
        raise HTTPException(status_code=404, detail="preset not found")
    return PresetResponse(preset_id=preset_id, name=rec["name"], config=rec["config"])


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: str, svc: PresetService = Depends(svc_dep)
) -> dict[str, str]:
    ok = svc.delete(preset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="preset not found")
    return {"deleted": preset_id}
