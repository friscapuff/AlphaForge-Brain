from __future__ import annotations

from typing import Any, Callable, Protocol

import numpy as np
import pandas as pd
from numpy.typing import NDArray


class _MetadataProto(Protocol):  # pragma: no cover - structural typing only
    anomaly_counters: dict[str, int]


_get_dataset_metadata: Callable[[], _MetadataProto] | None
try:  # Local import for anomaly counters; allows monkeypatch on module symbol
    from domain.data.ingest_nvda import get_dataset_metadata as _imported_get_md

    _get_dataset_metadata = _imported_get_md
except Exception:  # pragma: no cover - optional during early phases
    _get_dataset_metadata = None

get_dataset_metadata: Callable[[], _MetadataProto] | None = _get_dataset_metadata

try:  # Optional timeframe scaling hook
    from domain.risk.timeframe_scaling import maybe_scale
except Exception:  # pragma: no cover - defensive

    def maybe_scale(metric: float, bar_seconds: int | None) -> float:
        """Fallback no-op scaling when optional timeframe module absent."""
        return metric


def build_equity_curve(positions_df: pd.DataFrame) -> pd.DataFrame:
    """Build equity curve and per-bar simple returns.

    Expects columns: timestamp, equity
    If equity absent but cash/position + close exist in positions_df (not the case currently), we could derive; for now assume equity present.
    """
    if positions_df.empty:
        out = positions_df.iloc[0:0].copy()
        for col in ["equity", "return"]:
            if col not in out.columns:
                out[col] = []
        return out

    required_cols = {"timestamp", "equity"}
    missing_cols = required_cols.difference(positions_df.columns)
    if missing_cols:
        missing = ", ".join(sorted(missing_cols))
        raise ValueError(f"positions_df missing required columns: {missing}")

    timestamps = positions_df["timestamp"]
    equity = positions_df["equity"]
    eq = pd.DataFrame(
        {
            "timestamp": timestamps.to_numpy(copy=True),
            "equity": pd.to_numeric(equity, errors="coerce"),
        }
    )
    eq.sort_values("timestamp", inplace=True)
    equity_values = eq["equity"].to_numpy(dtype=float)
    returns = np.zeros_like(equity_values, dtype=float)
    if equity_values.size > 1:
        prev = equity_values[:-1]
        curr = equity_values[1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.divide(
                curr, prev, out=np.ones_like(curr, dtype=float), where=prev != 0.0
            )
        returns[1:] = ratio - 1.0
    eq["return"] = returns
    return eq


def _sharpe(returns: pd.Series | NDArray[np.float64]) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    mu = float(np.nanmean(arr))
    sigma = float(np.nanstd(arr, ddof=0))
    if sigma == 0.0 or np.isnan(sigma):
        return 0.0
    # Assuming returns are per-bar; no annualization (can be added later)
    return float(mu / sigma)


def _max_drawdown(equity: pd.Series | NDArray[np.float64]) -> float:
    arr = np.asarray(equity, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    running_max = np.maximum.accumulate(arr)
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdowns = np.divide(
            arr - running_max,
            running_max,
            out=np.zeros_like(arr),
            where=running_max != 0.0,
        )
    return float(np.min(drawdowns))  # negative number


def compute_metrics(
    trades_df: pd.DataFrame,
    equity_curve: pd.DataFrame,
    *,
    include_anomalies: bool = False,
) -> dict[str, Any]:
    """Compute baseline metrics.

    Metrics:
      total_return: final_eq / first_eq - 1
      sharpe: mean(return)/std(return)
      max_drawdown: minimum (equity/running_max - 1) (negative)
      trade_count: number of realized trades
    """
    if equity_curve.empty:
        base: dict[str, Any] = {
            "total_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "trade_count": len(trades_df),
        }
        if include_anomalies:
            if get_dataset_metadata is not None:
                try:  # pragma: no cover - small integration
                    counters = dict(get_dataset_metadata().anomaly_counters)
                except Exception:
                    counters = {}
            else:
                counters = {}
            # Normalize expected keys so downstream consumers/tests can rely on presence
            expected = [
                "duplicates_dropped",
                "rows_dropped_missing",
                "zero_volume_rows",
                "future_rows_dropped",
                "unexpected_gaps",
                "expected_closures",
            ]
            for k in expected:
                counters.setdefault(k, 0)
            base["anomaly_counters"] = counters
        return base

    eq_values = np.asarray(equity_curve["equity"], dtype=float)
    total_return = (
        float(eq_values[-1] / eq_values[0] - 1.0) if eq_values.size > 0 else 0.0
    )
    returns = np.asarray(equity_curve["return"], dtype=float)
    sharpe_raw = _sharpe(returns)
    # Attempt timeframe scaling (annualization) only if env flag set and metadata provides bar seconds
    bar_seconds: int | None = None
    if get_dataset_metadata is not None:
        try:  # pragma: no cover - integration guard
            md = get_dataset_metadata()
            bar_seconds = getattr(md, "observed_bar_seconds", None)
        except Exception:
            bar_seconds = None
    sharpe = maybe_scale(sharpe_raw, bar_seconds)
    max_dd = _max_drawdown(eq_values)
    out: dict[str, Any] = {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "trade_count": len(trades_df),
    }
    if include_anomalies:
        if get_dataset_metadata is not None:
            try:  # pragma: no cover - small integration
                counters = dict(get_dataset_metadata().anomaly_counters)
            except Exception:
                counters = {}
        else:
            counters = {}
        expected = [
            "duplicates_dropped",
            "rows_dropped_missing",
            "zero_volume_rows",
            "future_rows_dropped",
            "unexpected_gaps",
            "expected_closures",
        ]
        for k in expected:
            counters.setdefault(k, 0)
        out["anomaly_counters"] = counters
    return out


__all__ = ["build_equity_curve", "compute_metrics"]
