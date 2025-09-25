"""Immutable executed trade record.

T027 - Trade model

Scope:
* Pure data (no PnL calc here) used later by performance aggregation
* Deterministic hashing left to manifest layer (not duplicated)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, model_validator

from .base import BaseModelStrict


class TradeSide(str, Enum):  # FR-010
    BUY = "BUY"
    SELL = "SELL"


class Trade(BaseModelStrict):  # FR-010..FR-012
    ts: datetime = Field(description="Execution timestamp (UTC)")
    symbol: str
    side: TradeSide
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    strategy_id: str = Field(description="Link back to StrategyConfig.id")
    order_id: str | None = Field(default=None)
    run_id: str | None = Field(default=None, description="Assigned post-run")

    @model_validator(mode="after")
    def _sanity(self) -> Trade:
        if self.quantity * self.price <= 0:
            raise ValueError("quantity * price must be positive")
        return self


__all__ = ["Trade", "TradeSide"]
