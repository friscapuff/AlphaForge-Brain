"""JournalingAggregate model (Phase 016 / T028).

Captures per-run aggregation metrics for enriched journaling artifacts. The
model keeps payloads schema-versioned to ensure deterministic hashing and
contract validation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import BaseModelStrict


class JournalingAggregate(BaseModelStrict):
    run_id: str
    schema_version: str = Field(default="2025.10.16")
    generated_at: datetime
    artifact_hash: str
    context_version: str = Field(default="enrichment.context.v1")
    expectancy_by_strategy: dict[str, float] = Field(default_factory=dict)
    checklist_adherence: dict[str, float] = Field(default_factory=dict)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    mae_mfe_stats: dict[str, float] = Field(default_factory=dict)
    breach_flags: list[str] = Field(default_factory=list)
    source_artifacts: list[str] = Field(default_factory=list)


__all__ = ["JournalingAggregate"]
