"""CompletedTrade aggregate model.

FR Cross-Refs: FR-004 (Round-trip aggregation), FR-005 (Canonical trade mapping), FR-006 (Hash exclusion policy for trade_model_version), FR-008 (Metrics stabilization foundation).

T012 - CompletedTrade Model (FR-004, FR-005, FR-006)

Represents a round-trip position lifecycle derived from one or more Fill
instances. Provides pre-computed performance attributes to simplify downstream
reporting, validation, and hashing.

Fields:
  id: stable identifier (hash of entry ts + symbol + index or DB PK when persisted)
  symbol: trading symbol (currently single-symbol engine)
  entry_ts / exit_ts: temporal bounds of the lifecycle (exit_ts may equal entry_ts for immediate round-trips)
  entry_price / exit_price: VWAP-based derivations from aggregated fills
  quantity: total signed position size opened (positive long, negative short)
  pnl: realized profit/loss (quote currency units)
  return_pct: (exit_price - entry_price)/entry_price * direction_sign
  holding_period_secs: duration of the trade in seconds
  fills: optional embedded list of Fill objects (for traceability) — may be omitted in lightweight payloads

Determinism:
  - All numeric fields should be computed with stable ordering & rounding upstream.
  - This model does not perform calculations; expects fully prepared values.
  - Pnl & return_pct must align with equity normalization removal plan (Phase 3) without 1_000_000 scaling.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import BaseModelStrict
from .fill import Fill


class CompletedTrade(BaseModelStrict):  # Canonical aggregate FR set
    id: str
    symbol: str
    entry_ts: datetime
    exit_ts: datetime
    entry_price: float = Field(ge=0)
    exit_price: float = Field(ge=0)
    quantity: float
    pnl: float
    return_pct: float
    holding_period_secs: float = Field(ge=0)
    fills: list[Fill] | None = Field(
        default=None, description="Optional embedded fills for traceability"
    )


__all__ = ["CompletedTrade"]
