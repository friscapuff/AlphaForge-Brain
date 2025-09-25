"""Optional risk scaling hook (Phase K T060).

When environment variable AF_TIMEFRAME_RISK_SCALE=1 is set, provide helper to
derive annualization factors based on timeframe bar seconds (approximation).

Currently dormant: integrate into risk models by opting in explicitly.
"""

from __future__ import annotations

import os


def annualization_factor(bar_seconds: int | None) -> float:
    if not bar_seconds or bar_seconds <= 0:
        return 1.0
    # Approximate trading year seconds (252 * 6.5h for equities ~ 589,6800s) but using full-day baseline for simplicity
    trading_year_seconds = 252 * 24 * 3600  # intentionally conservative until refined
    return trading_year_seconds / bar_seconds


def maybe_scale(metric: float, bar_seconds: int | None) -> float:
    if os.getenv("AF_TIMEFRAME_RISK_SCALE") != "1":
        return metric
    return metric * annualization_factor(bar_seconds)


__all__ = ["annualization_factor", "maybe_scale"]
