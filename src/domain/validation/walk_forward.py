from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

from .utils import extract_returns


def _fold_metrics(returns: np.ndarray[Any, Any]) -> dict[str, float]:
    if returns.size == 0:
        return {"sharpe": 0.0, "return": 0.0, "max_dd": 0.0}
    mean = returns.mean()
    std = returns.std(ddof=0)
    sharpe = float((mean / std) * np.sqrt(252)) if std > 0 else 0.0
    cum = np.cumprod(1 + returns)
    ret = float(cum[-1] - 1)
    running_max = np.maximum.accumulate(cum)
    dd = (cum / running_max) - 1.0
    max_dd = float(dd.min())
    return {"sharpe": sharpe, "return": ret, "max_dd": max_dd}


def walk_forward_report(
    trades_df: pd.DataFrame,
    positions_df: pd.DataFrame | None = None,
    *,
    n_folds: int = 4,
    method: Literal["expanding", "rolling"] = "expanding",
) -> list[dict[str, Any]]:
    """Produce walk-forward performance summary across temporal folds.

    For simplicity we partition by timestamp range using trades_df timestamps.
    Each fold's metrics computed on its own subset only (no training effect modeled yet).
    """
    if n_folds <= 0:
        raise ValueError("n_folds must be > 0")
    if trades_df is None or trades_df.empty:
        return []
    # Prefer exit_ts (completed trade timestamp), else entry_ts
    if "exit_ts" in trades_df.columns:
        ts_col = "exit_ts"
    elif "entry_ts" in trades_df.columns:
        ts_col = "entry_ts"
    else:
        # fallback to any timestamp-like column
        for c in ["timestamp", "time", "ts"]:
            if c in trades_df.columns:
                ts_col = c
                break
        else:
            raise ValueError("No timestamp column found in trades_df (expected exit_ts or entry_ts)")
    df = trades_df.copy().sort_values(ts_col).reset_index(drop=True)
    total = len(df)
    if total < n_folds:
        n_folds = total
    fold_sizes = [total // n_folds] * n_folds
    remainder = total % n_folds
    for i in range(remainder):
        fold_sizes[i] += 1
    boundaries = []
    start = 0
    for sz in fold_sizes:
        end = start + sz
        boundaries.append((start, end))
        start = end

    reports: list[dict[str, Any]] = []
    for i, (s, e) in enumerate(boundaries, start=1):
        segment = df.iloc[s:e]
        # compute returns for just these trades
        returns_series = extract_returns(segment, None)
        metrics = _fold_metrics(returns_series.to_numpy(dtype=float))
        reports.append({
            "fold": i,
            "start": segment[ts_col].iloc[0],
            "end": segment[ts_col].iloc[-1],
            "n_trades": len(segment),
            **metrics,
        })
    return reports


__all__ = ["walk_forward_report"]
