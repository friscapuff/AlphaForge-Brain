"""Equity curve bar snapshot.

T028 - EquityBar model (FR-013..FR-015).

Captures per-bar state used for performance stats & validation. Aggregation
of series metrics (CAGR, Sharpe, etc.) occurs in service layer / metrics core.

Semantics:
    nav: Unscaled equity (Phase 3 will remove any legacy 1_000_000 scaling; current model assumes already normalized when flag `AF_EQUITY_NORMALIZER_V2` enabled).
    peak_nav: Running maximum nav up to and including this bar.
    drawdown: (peak_nav - nav)/peak_nav (non-negative). Small FP discrepancies tolerated by validator epsilon.
    gross_exposure: Sum of absolute notionals; net_exposure: signed notional (long-positive/short-negative).
    trade_count_cum: Cumulative realized trade count at this bar boundary.

Determinism:
    - Relationships validator ensures drawdown consistency.
    - Any future epsilon adjustments must route through settings.determinism.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator
from settings.determinism import DRAWNDOWN_EPSILON

from .base import BaseModelStrict


class EquityBar(BaseModelStrict):  # FR-013..FR-015
    ts: datetime
    nav: float = Field(gt=0, description="Equity curve net asset value")
    peak_nav: float = Field(gt=0)
    drawdown: float = Field(ge=0)
    gross_exposure: float = Field(ge=0)
    net_exposure: float
    trade_count_cum: int = Field(ge=0)

    @model_validator(mode="after")
    def _relationships(self) -> EquityBar:
        if self.peak_nav < self.nav:
            # allow slight FP noise? keep strict for now (determinism requirement)
            raise ValueError("peak_nav must be >= nav")
        expected_dd = (self.peak_nav - self.nav) / self.peak_nav
        # Accept small floating discrepancy (configurable via DRAWNDOWN_EPSILON)
        if abs(expected_dd - self.drawdown) > DRAWNDOWN_EPSILON:
            raise ValueError("drawdown inconsistent with nav/peak_nav")
        return self


__all__ = ["EquityBar"]
