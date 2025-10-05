from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

from .utils import extract_returns


def _sharpe(returns: np.ndarray[Any, Any]) -> float:
    if returns.size == 0:
        return 0.0
    mean = returns.mean()
    std = returns.std(ddof=0)
    if std == 0:
        return 0.0
    return float(
        (mean / std) * np.sqrt(252 * 24 * 60)
    )  # scale minute-level to annual (~252 trading days)


def monte_carlo_slippage(
    trades_df: pd.DataFrame,
    positions_df: pd.DataFrame | None = None,
    *,
    n_iter: int = 300,
    model: Literal["normal", "uniform"] = "normal",
    params: dict[str, Any] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Monte Carlo stress test applying random additional slippage/fees to trades.

    Produces distribution of Sharpe deltas versus observed Sharpe.
    Returns dict keys: distribution (np.ndarray), observed_metric (baseline Sharpe), p_value (Pr(delta >= 0)).
    """
    if n_iter <= 0:
        raise ValueError("n_iter must be > 0")
    params = params or {}
    base_returns = extract_returns(trades_df, positions_df)
    if base_returns.empty:
        return {
            "distribution": np.array([], dtype=float),
            "observed_metric": 0.0,
            "p_value": 1.0,
        }
    arr = base_returns.to_numpy(dtype=float)
    baseline_sharpe = _sharpe(arr)
    rng = np.random.default_rng(seed)

    # Determine noise model: we perturb returns downward to simulate higher costs.
    # noise represents extra cost fraction; adjusted_return = return - noise
    if model == "normal":
        mu = float(params.get("mu", 0.0001))  # 1 bp expected extra cost
        sigma = float(params.get("sigma", 0.0002))

        def sample_noise(size: int) -> np.ndarray[Any, Any]:
            return np.clip(rng.normal(mu, sigma, size=size), 0, None)

    elif model == "uniform":
        low = float(params.get("low", 0.0))
        high = float(params.get("high", 0.0004))

        def sample_noise(size: int) -> np.ndarray[Any, Any]:
            return rng.uniform(low, high, size=size)

    else:
        raise ValueError(f"Unsupported model: {model}")

    dist = np.empty(n_iter, dtype=float)
    for i in range(n_iter):
        noise = sample_noise(arr.size)
        stressed = arr - noise
        dist[i] = _sharpe(stressed) - baseline_sharpe
    # p-value: probability that Sharpe delta >= 0 (i.e., costs not hurting performance)
    count_ge = int(np.sum(dist >= 0))
    p_value = (count_ge + 1) / (n_iter + 1)
    return {
        "distribution": dist,
        "observed_metric": baseline_sharpe,
        "p_value": float(p_value),
    }


__all__ = ["monte_carlo_slippage"]
