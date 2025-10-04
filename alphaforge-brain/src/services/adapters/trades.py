"""Legacy ↔ Canonical trade/equity adapters.

FR Cross-Refs: FR-004..FR-008 (unified trade pipeline), FR-013 (Equity consistency pre-normalization), FR-015 (Hash comparability guarantee).

T017 - Compatibility Adapters (FR-004..FR-008 integration surface)

These helpers allow phased migration by materializing canonical Fill and
CompletedTrade models from existing legacy structures without changing core
execution pipeline immediately.

Design Notes:
- Pure functions; no side effects or DB calls.
- Accept generic sequences to minimize coupling; callers perform any ORM
detachment or DataFrame slicing first.
- VWAP and holding period computations are delegated to upstream pipeline; in
this first scaffold we only map field names and basic derivations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Sequence

try:  # Local imports inside try for early test harness before full refactor
    from models.completed_trade import CompletedTrade
    from models.fill import Fill
except Exception:  # pragma: no cover
    Fill = object  # type: ignore
    CompletedTrade = object  # type: ignore


# Placeholder type hints for legacy structures; refine when integrating.
class _LegacyFill:  # pragma: no cover - descriptive only
    ts: datetime
    quantity: float
    price: float
    order_id: str
    run_id: str | None


class _LegacyTrade:  # pragma: no cover
    entry_ts: datetime
    exit_ts: datetime
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    return_pct: float
    holding_period_bars: int
    symbol: str


def legacy_trades_to_completed(legacy: Sequence[_LegacyTrade]) -> list[Any]:
    """Convert legacy trade objects to canonical CompletedTrade list.

    Assumptions:
      - Legacy trade already aggregates fills into entry/exit.
      - holding_period_secs derived from bars * 60 for now (placeholder) — refined when bar duration available.
    """
    out: list[Any] = []
    for i, t in enumerate(legacy):
        try:
            secs = getattr(t, "holding_period_bars", 0) * 60
            out.append(
                CompletedTrade(  # type: ignore[arg-type]
                    id=f"legacy::{i}",
                    symbol=getattr(t, "symbol", "UNKNOWN"),
                    entry_ts=t.entry_ts,
                    exit_ts=t.exit_ts,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    quantity=t.qty,
                    pnl=t.pnl,
                    return_pct=t.return_pct,
                    holding_period_secs=secs,
                    fills=None,
                )
            )
        except Exception:
            # Skip malformed legacy entries silently in scaffold; later versions will log.
            continue
    return out


def legacy_fills_to_fills(legacy: Iterable[_LegacyFill]) -> list[Any]:
    """Convert legacy fill-like objects to canonical Fill list."""
    out: list[Any] = []
    for f in legacy:
        try:
            out.append(
                Fill(  # type: ignore[arg-type]
                    ts=f.ts,
                    order_id=getattr(f, "order_id", "unknown"),
                    size=f.quantity,
                    price=f.price,
                    run_id=getattr(f, "run_id", None),
                )
            )
        except Exception:
            continue
    return out


__all__ = ["legacy_trades_to_completed", "legacy_fills_to_fills"]
