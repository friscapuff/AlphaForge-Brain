"""Equity curve bar snapshot.

T028 - EquityBar model

Captures per-bar state used for performance stats & validation. Aggregation
of series metrics (CAGR, Sharpe, etc.) will occur in service layer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

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
        # Accept small floating discrepancy
        if abs(expected_dd - self.drawdown) > 1e-9:
            raise ValueError("drawdown inconsistent with nav/peak_nav")
        return self


__all__ = ["EquityBar"]
