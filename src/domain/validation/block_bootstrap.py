from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .utils import extract_returns, sample_block_indices


def block_bootstrap(
    trades_df: pd.DataFrame,
    positions_df: pd.DataFrame | None = None,
    *,
    n_iter: int = 500,
    block_size: int = 5,
    seed: int | None = None,
) -> dict[str, float | np.ndarray[Any, Any]]:
    """Block bootstrap for mean return preserving short-term dependence.

    Returns dict: {"distribution", "observed_mean", "mean", "p_value"}
    p_value one-sided Pr(bootstrap_mean >= observed_mean).
    Deterministic with given seed.
    """
    if n_iter <= 0:
        raise ValueError("n_iter must be > 0")
    returns = extract_returns(trades_df, positions_df)
    if returns.empty:
        return {
            "distribution": np.array([], dtype=float),
            "observed_mean": 0.0,
            "mean": 0.0,
            "p_value": 1.0,
        }
    arr = returns.to_numpy(dtype=float)
    n_obs = len(arr)
    block_size = max(1, min(block_size, n_obs))
    rng = np.random.default_rng(seed)
    observed_mean = float(arr.mean())
    dist = np.empty(n_iter, dtype=float)
    for i in range(n_iter):
        blocks = sample_block_indices(n_obs, block_size, rng)
        # Concatenate sampled blocks (truncate to n_obs to keep length consistent)
        sampled = []
        for start, end in blocks:
            sampled.append(arr[start:end])
            if sum(len(x) for x in sampled) >= n_obs:
                break
        cat = np.concatenate(sampled)[:n_obs]
        dist[i] = float(cat.mean())
    # p-value (one sided positive)
    count_ge = int(np.sum(dist >= observed_mean))
    p_value = (count_ge + 1) / (n_iter + 1)
    return {
        "distribution": dist,
        "observed_mean": observed_mean,
        "mean": float(dist.mean()),
        "p_value": float(p_value),
    }


__all__ = ["block_bootstrap"]
