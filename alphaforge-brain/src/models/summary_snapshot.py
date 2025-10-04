"""High level run summary snapshot.

T032 - SummarySnapshot model

Used for quick reporting & UI surfaces; heavy computations performed in
services and persisted as this immutable summary.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from .base import BaseModelStrict


class SummarySnapshot(BaseModelStrict):  # FR-030..FR-035
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_return: float | None = None
    cagr: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    calmar: float | None = None
    trade_count: int | None = None
    caution_metric_count: int = 0
    violation_metric_count: int = 0
    notes: list[str] = Field(default_factory=list)


__all__ = ["SummarySnapshot"]
