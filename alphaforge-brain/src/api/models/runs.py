from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RunCreateResponse(BaseModel):
    run_id: str
    run_hash: str
    status: str
    created_at: datetime
    created: bool
    api_version: str | None = None
    schema_version: str | None = None
    content_hash: str | None = None

    model_config = ConfigDict(extra="allow")


class RunListItem(BaseModel):
    run_hash: str
    created_at: datetime | None = None
    status: str = "SUCCEEDED"

    model_config = ConfigDict(extra="allow")


class RunListResponse(BaseModel):
    items: list[RunListItem]

    model_config = ConfigDict(extra="allow")


class PromotionRequest(BaseModel):
    waiver_id: str | None = None

    model_config = ConfigDict(extra="allow")


class PromotionResponse(BaseModel):
    run_hash: str
    status: str
    processed_at: datetime

    model_config = ConfigDict(extra="allow")


class ArtifactDescriptor(BaseModel):
    name: str
    sha256: str
    size: int

    model_config = ConfigDict(extra="allow")


class RunDetailResponse(BaseModel):
    run_id: str
    run_hash: str
    status: str
    phase: str
    artifacts: list[ArtifactDescriptor]
    summary: dict[str, Any] | None = None
    data_hash: str | None = None
    calendar_id: str | None = None
    validation_summary: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    api_version: str | None = None
    schema_version: str | None = None
    content_hash: str | None = None
    pinned: bool | None = None
    retention_state: str | None = None
    metrics_hash: str | None = None
    equity_curve_hash: str | None = None
    validation_schema_version: int | None = None
    validation_manifest: dict[str, Any] | None = None
    validation_significance: str | None = None
    validation_manifest_hash: str | None = None
    validation_status: str | None = None
    trust_gate: dict[str, Any] | None = None
    persistence: dict[str, Any] | None = None
    accounting: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class RunHashesResponse(BaseModel):
    run_hash: str
    manifest_hash: str | None = None
    metrics_hash: str | None = None
    equity_curve_hash: str | None = None
    provenance_hash: str | None = None
    api_version: str | None = None
    validation_manifest_hash: str | None = None
    trust_gate_signature: str | None = None

    model_config = ConfigDict(extra="allow")


__all__ = [
    "ArtifactDescriptor",
    "PromotionRequest",
    "PromotionResponse",
    "RunCreateResponse",
    "RunDetailResponse",
    "RunHashesResponse",
    "RunListItem",
    "RunListResponse",
]
