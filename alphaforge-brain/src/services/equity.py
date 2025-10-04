"""Equity curve aggregation (T038).

Simplified implementation accumulating NAV based on trade cash flows.
Assumptions: starting NAV = 1.0; trade price * quantity impacts cash then
unrealized PnL not modeled (placeholder). Exposure approximated by abs(position * price).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from models.equity_bar import EquityBar
from models.trade import Trade, TradeSide


@dataclass
class EquityState:
    nav: float = 1.0
    peak: float = 1.0
    position: float = 0.0
    trade_count: int = 0


def build_equity(trades: Iterable[Trade]) -> list[EquityBar]:
    bars: list[EquityBar] = []
    state = EquityState()
    # Sort trades deterministically by timestamp then symbol for reproducibility
    ordered = sorted(trades, key=lambda t: (t.ts, t.symbol))
    for t in ordered:
        state.trade_count += 1
        # Cash flow impact (BUY decreases nav, SELL increases) simplified
        cash_flow = (
            -t.price * t.quantity if t.side == TradeSide.BUY else t.price * t.quantity
        )
        state.nav += (
            cash_flow / 1_000_000
        )  # scale factor placeholder to keep nav sensible
        if state.nav <= 0:
            state.nav = 1e-9  # avoid zero/negative for log metrics downstream
        if state.nav > state.peak:
            state.peak = state.nav
        # Position update
        if t.side == TradeSide.BUY:
            state.position += t.quantity
        else:
            state.position -= t.quantity
        drawdown = (state.peak - state.nav) / state.peak if state.peak > 0 else 0.0
        # exposures (approximate) using trade price as proxy for mark
        gross_exposure = abs(state.position * t.price)
        net_exposure = state.position * t.price
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
