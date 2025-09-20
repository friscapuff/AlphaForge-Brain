from __future__ import annotations

from typing import Any

import pandas as pd


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

    if "equity" not in positions_df.columns:
        raise ValueError("positions_df must contain 'equity' column")

    eq = positions_df[["timestamp", "equity"]].copy()
    eq.sort_values("timestamp", inplace=True)
    eq["equity"] = eq["equity"].astype(float)
    eq["return"] = eq["equity"].pct_change().fillna(0.0)
    return eq


def _sharpe(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    mu = returns.mean()
    sigma = returns.std(ddof=0)
    if sigma == 0:
        return 0.0
    # Assuming returns are per-bar; no annualization (can be added later)
    return float(mu / sigma)


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdowns = (equity - running_max) / running_max
    return float(drawdowns.min())  # negative number


def compute_metrics(trades_df: pd.DataFrame, equity_curve: pd.DataFrame) -> dict[str, Any]:
    """Compute baseline metrics.

    Metrics:
      total_return: final_eq / first_eq - 1
      sharpe: mean(return)/std(return)
      max_drawdown: minimum (equity/running_max - 1) (negative)
      trade_count: number of realized trades
    """
    if equity_curve.empty:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "trade_count": int(len(trades_df))}

    eq = equity_curve["equity"].astype(float)
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1.0) if len(eq) > 0 else 0.0
    sharpe = _sharpe(equity_curve["return"].astype(float))
    max_dd = _max_drawdown(eq)
    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "trade_count": int(len(trades_df)),
    }


__all__ = ["build_equity_curve", "compute_metrics"]
