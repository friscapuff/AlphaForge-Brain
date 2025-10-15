"""Atomic execution fill record.

FR Cross-Refs: FR-001 (Atomic fill semantics), FR-002 (Deterministic hashing context), FR-003 (Adapter layering).

T011 - Fill Model (FR-001, FR-002, FR-003 partial references)

Represents a single executed order slice. Higher-level CompletedTrade aggregates
multiple fills across entry/exit lifecycle.

Notable Semantics:
  - size: signed quantity (positive long buy, negative sell or short open/close)
  - price: execution price (float) as provided by simulator/exchange adapter
  - ts: execution timestamp (UTC naive or aware normalized upstream)
  - order_id: logical grouping identifier (strategy emission linkage)
  - run_id: optional foreign key to parent run for persistence layer
  - stop_id: optional protective stop reference (Phase 016 enrichment)
  - target_id: optional profit target reference
  - risk_tier: categorical position sizing tier ("conservative", "moderate", "aggressive")
  - expectancy_inputs: numeric inputs for expectancy/R-multiple calculations (e.g., risk unit, spread)

Determinism Considerations:
  - All numeric fields must be exact for hashing; price normalization handled upstream.
  - No derived fields stored here to keep atomic fill immutable & minimal.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import BaseModelStrict


class Fill(BaseModelStrict):  # FR Aggregate Component
    ts: datetime
    order_id: str
    size: float = Field(
        description="Signed quantity; positive for buy/add, negative for sell/reduce"
    )
    price: float = Field(ge=0)
    run_id: str | None = Field(
        default=None, description="Optional run linkage (persistence)"
    )
    stop_id: str | None = Field(default=None, description="Protective stop identifier")
    target_id: str | None = Field(default=None, description="Profit target identifier")
    risk_tier: str | None = Field(
        default=None,
        description="Risk tier classification (conservative/moderate/aggressive)",
    )
    expectancy_inputs: dict[str, float] | None = Field(
        default=None,
        description="Expectancy calculation inputs (risk unit, spread, fees)",
    )


# Future extension hooks (slippage attribution, fee breakdown) intentionally omitted for initial unification phase.


__all__ = ["Fill"]
