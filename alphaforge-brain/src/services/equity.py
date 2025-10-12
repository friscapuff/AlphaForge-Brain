"""Equity curve aggregation (T038).

Simplified implementation accumulating NAV based on trade cash flows.
Assumptions: starting NAV = 1.0; trade price * quantity impacts cash then
unrealized PnL not modeled (placeholder). Exposure approximated by abs(position * price).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from models.equity_bar import EquityBar


@dataclass
class EquityState:
    nav: float = 1.0
    peak: float = 1.0
    position: float = 0.0
    trade_count: int = 0


def _is_buy(side: Any, qty: float | None) -> bool:
    # Accept Enum with name/value, string, or infer from signed qty
    side_text: str | None = None
    if side is not None:
        val = getattr(side, "name", None) or getattr(side, "value", None)
        if isinstance(val, str):
            side_text = val
        if side_text is None and isinstance(side, str):
            side_text = side
    if side_text is not None:
        return side_text.upper() == "BUY"
    if qty is not None:
        try:
            return float(qty) > 0
        except Exception:
            return False
    return False


def build_equity(trades: Iterable[Any]) -> list[EquityBar]:
    bars: list[EquityBar] = []
    state = EquityState()
    # Sort trades deterministically by timestamp then symbol for reproducibility
    ordered = sorted(trades, key=lambda t: (t.ts, getattr(t, "symbol", "")))
    for t in ordered:
        state.trade_count += 1
        # Cash flow impact (BUY decreases nav, SELL increases) simplified
        price = t.price
        qty_raw = getattr(t, "quantity", None)
        if qty_raw is None:
            qty_raw = getattr(t, "size", None)
        qty_abs = abs(float(qty_raw)) if qty_raw is not None else 0.0
        side_attr = getattr(t, "side", None)
        is_buy = _is_buy(
            side_attr, float(qty_raw) if isinstance(qty_raw, (int, float)) else None
        )
        cash_flow = (-price * qty_abs) if is_buy else (price * qty_abs)
        state.nav += (
            cash_flow / 1_000_000
        )  # scale factor placeholder to keep nav sensible
        if state.nav <= 0:
            state.nav = 1e-9  # avoid zero/negative for log metrics downstream
        if state.nav > state.peak:
            state.peak = state.nav
        # Position update
        state.position += qty_abs if is_buy else -qty_abs
        drawdown = (state.peak - state.nav) / state.peak if state.peak > 0 else 0.0
        # exposures (approximate) using trade price as proxy for mark
        gross_exposure = abs(state.position * price)
        net_exposure = state.position * price
        bars.append(
            EquityBar(
                ts=t.ts,
                nav=state.nav,
                peak_nav=state.peak,
                drawdown=drawdown,
                gross_exposure=gross_exposure,
                net_exposure=net_exposure,
                trade_count_cum=state.trade_count,
            )
        )
    return bars


__all__ = ["build_equity"]
