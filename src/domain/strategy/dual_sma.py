from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .base import strategy


@strategy("dual_sma")
def dual_sma_strategy(df: pd.DataFrame, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Generate long/flat/short signals from pre-computed short & long SMA columns.

    Assumes indicator step has already added columns: `sma_short_<short_window>` and `sma_long_<long_window>`.
    Signals:
      +1 when short crosses above long (and both valid)
      -1 when short crosses below long
       0 otherwise (carry forward last non-zero position not implemented yet; just immediate signals).
    """
    if params is None:
        params = {}
    short_w = int(params.get("short_window", 10))
    long_w = int(params.get("long_window", 50))
    if short_w < 1:
        raise ValueError("short_window must be >= 1")
    if long_w <= short_w:
        raise ValueError("long_window must be > short_window")

    short_col = f"sma_short_{short_w}"
    long_col = f"sma_long_{long_w}"
    if short_col not in df.columns or long_col not in df.columns:
        raise ValueError("Required SMA columns missing; run indicator first")

    out = df.copy()
    short = out[short_col]
    long = out[long_col]

    # Compute raw comparison
    gt = short > long
    lt = short < long

    signal = np.full(len(out), np.nan)

    prev_gt = None
    prev_lt = None
    for i in range(len(out)):
        s_val = short.iloc[i]
        l_val = long.iloc[i]
        if np.isnan(s_val) or np.isnan(l_val):
            continue
        if gt.iloc[i] and not (prev_gt):  # crossed above
            signal[i] = 1
        elif lt.iloc[i] and not (prev_lt):  # crossed below
            signal[i] = -1
        else:
            signal[i] = 0
        prev_gt = gt.iloc[i]
        prev_lt = lt.iloc[i]

    out["signal"] = signal
    return out

__all__ = ["dual_sma_strategy"]
