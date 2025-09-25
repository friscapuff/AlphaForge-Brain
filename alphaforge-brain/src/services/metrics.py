"""Metrics calculator (T039).

Computes basic performance statistics from an equity bar series.
Simplifications: using bar-based returns; volatility = std of returns.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt
from statistics import mean, pstdev

from ..models.equity_bar import EquityBar


def _returns(bars: list[EquityBar]) -> list[float]:
    rets: list[float] = []
    prev: EquityBar | None = None
    for b in bars:
        if prev is not None:
            rets.append((b.nav - prev.nav) / prev.nav)
        prev = b
    return rets


def compute_metrics(bars: Iterable[EquityBar]) -> dict[str, float]:
    series = list(bars)
    if not series:
        return {}
    r = _returns(series)
    if not r:
        return {"total_return": 0.0}
    total_return = series[-1].nav / series[0].nav - 1 if series[0].nav > 0 else 0.0
    avg = mean(r)
    vol = pstdev(r) if len(r) > 1 else 0.0
    sharpe = 0.0 if vol <= 0 else (avg / vol * sqrt(len(r)))
    max_dd = max((b.drawdown for b in series), default=0.0)
    return {
        "total_return": total_return,
        "avg_return": avg,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
    }


__all__ = ["compute_metrics"]
