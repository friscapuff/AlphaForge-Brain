"""API schema models for sweep status responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SweepParameterAssignmentModel(BaseModel):
    name: str
    value: Any


class SweepCombinationModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    combination_id: str
    parameters: list[SweepParameterAssignmentModel] = Field(default_factory=list)
    run_hash: str | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    trust_gate_summary: dict[str, Any] | None = None


class SweepAggregateModel(BaseModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    average_duration_ms: float | None = None
    storage_bytes: int | float | None = None


class TelemetryReferenceModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    manifest_path: str | None = None
    metrics_namespace: str | None = None


class TickerStatusModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    ticker: str
    combination_cap: int
    cap_status: str
    data_quality_status: str
    variance_metrics: dict[str, Any] = Field(default_factory=dict)
    manifest_path: str | None = None
    partial_execution_reason: str | None = None


class SweepStatusModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    sweep_id: str
    status: str
    combination_cap: int
    submitted_at: datetime
    completed_at: datetime | None = None
    initiator: str | None = None
    combinations: list[SweepCombinationModel] = Field(default_factory=list)
    aggregates: SweepAggregateModel = Field(default_factory=SweepAggregateModel)
    telemetry_reference: TelemetryReferenceModel | None = None
    tickers: list[TickerStatusModel] = Field(default_factory=list)
    derived_metrics: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    trust_gates: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "SweepAggregateModel",
    "SweepCombinationModel",
    "SweepParameterAssignmentModel",
    "SweepStatusModel",
    "TelemetryReferenceModel",
    "TickerStatusModel",
]
