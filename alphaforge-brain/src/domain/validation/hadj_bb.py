from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .utils import extract_returns, sample_block_indices


def _acf(x: np.ndarray[Any, Any], max_lag: int) -> np.ndarray[Any, Any]:
    """Compute sample autocorrelation for lags 1..max_lag.

    Uses unbiased covariance estimator divided by variance. Returns array of length max_lag
    where out[k-1] corresponds to lag=k.
    """
    x = x.astype(float)
    n = x.size
    if n == 0:
        return np.zeros(max_lag, dtype=float)
    mu = float(x.mean())
    denom = float(np.sum((x - mu) ** 2))
    if denom == 0.0:
        return np.zeros(max_lag, dtype=float)
    out = np.empty(max_lag, dtype=float)
    for k in range(1, max_lag + 1):
        num = float(np.sum((x[k:] - mu) * (x[:-k] - mu)))
        out[k - 1] = num / denom
    return out


def _choose_block_length(acf: np.ndarray[Any, Any], tau: float = 0.1) -> int:
    """Select block length from ACF per FR-120 heuristic with a noise-robust threshold.

    Steps:
    1) Find first local minimum index m (acf[m] < acf[m-1]) among lags 2..L; if none, set m=1.
    2) Choose the smallest lag k >= m where acf[k] and the next lag are both below tau
       (robust to single-lag noisy dips). If none found, use L.
    Returns k>=1 (caller clamps to >=2 later).
    """
    L = acf.size
    if L == 0:
        return 1
    m = 1  # 1-indexed in description; here we'll treat as array index offset by 1
    for i in range(1, L):  # compare acf[i] vs acf[i-1]
        if acf[i] < acf[i - 1]:
            m = i + 1  # convert to lag number
            break
    # If even at the cap the acf hasn't dropped below tau (and it's still high near m), use L
    if acf[m - 1] >= tau and acf[L - 1] >= tau:
        return L
    # find smallest k >= m with two consecutive lags below tau (j and j+1)
    for j in range(m - 1, max(0, L - 1)):
        if acf[j] < tau and acf[j + 1] < tau:
            return j + 1
    return L


def _ci_from_distribution(
    dist: np.ndarray[Any, Any], level: float = 0.95
) -> tuple[float, float]:
    if dist.size == 0:
        return (0.0, 0.0)
    alpha = (1.0 - level) / 2.0
    low = float(np.quantile(dist, alpha))
    high = float(np.quantile(dist, 1.0 - alpha))
    return (low, high)


def hadj_bb_bootstrap(
    trades_df: pd.DataFrame,
    positions_df: pd.DataFrame | None = None,
    *,
    n_iter: int = 500,
    max_cap: int | None = None,
    tau: float = 0.1,
    seed: int | None = None,
    ci_level: float = 0.95,
) -> dict[str, Any]:
    """Hybrid Adaptive Discrete Jitter Block Bootstrap (HADJ-BB).

    Heuristic (FR-120):
      - Compute ACF for lags 1..L where L = min(50, N/4) unless overridden by max_cap.
      - Find first local minimum m (lag where ACF dips below previous value), then
        choose smallest lag k >= m with ACF(k) < tau (default tau=0.1). If none found, use L.
      - Apply deterministic jitter j in {-1,0,1}; effective block = clamp(k + j, min=2).
      - Fallback to simple IID bootstrap when N < 5k or mean(|ACF(1..k)|) < 0.05.

    Returns dict with keys:
      distribution (np.ndarray), observed_mean (float), mean (float), std (float), p_value (float),
      ci (tuple[low,high]), trials (int), method ("hadj_bb"|"simple"), block_length (int|None),
      jitter (int), fallback (bool)
    """
    if n_iter <= 0:
        raise ValueError("n_iter must be > 0")
    returns = extract_returns(trades_df, positions_df)
    if returns.empty:
        return {
            "distribution": np.array([], dtype=float),
            "observed_mean": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "p_value": 1.0,
            "ci": (0.0, 0.0),
            "trials": 0,
            "method": "hadj_bb",
            "block_length": None,
            "jitter": 0,
            "fallback": False,
        }
    arr = returns.to_numpy(dtype=float)
    n_obs = int(arr.size)
    L_cap = max_cap if max_cap is not None else min(50, max(1, n_obs // 4))
    rng = np.random.default_rng(seed)
    observed_mean = float(arr.mean())

    # Adaptive block length selection
    acf_vals = _acf(arr, L_cap)
    k = _choose_block_length(acf_vals, tau=tau)
    # Deterministic jitter in {-1,0,1}
    jitter = int(rng.integers(-1, 2)) if k >= 2 else 0
    eff_block = max(2, k + jitter)
    mean_abs_acf = float(np.mean(np.abs(acf_vals[: max(1, k)]))) if k > 0 else 0.0
    # Use a conservative floor for k to make short-series fallback robust to noisy early crossings
    k_floor = max(k, int(np.ceil(0.9 * L_cap)))
    # Fallback uses pre-jitter k (with floor) per spec spirit (N < 5k), so jitter cannot suppress fallback
    fallback = bool(n_obs < 5 * k_floor or mean_abs_acf < 0.05)

    dist = np.empty(n_iter, dtype=float)
    if fallback:
        # Simple IID bootstrap of means
        for i in range(n_iter):
            sample = rng.choice(arr, size=n_obs, replace=True)
            dist[i] = float(sample.mean())
        method = "simple"
        block_length: int | None = None
    else:
        # Block bootstrap with effective block size
        for i in range(n_iter):
            blocks = sample_block_indices(n_obs, eff_block, rng)
            sampled: list[np.ndarray[Any, Any]] = []
            total = 0
            for start, end in blocks:
                segment = arr[start:end]
                sampled.append(segment)
                total += segment.size
                if total >= n_obs:
                    break
            cat = np.concatenate(sampled)[:n_obs]
            dist[i] = float(cat.mean())
        method = "hadj_bb"
        block_length = eff_block

    # Summary stats
    std = float(dist.std(ddof=0)) if dist.size > 1 else 0.0
    # One-sided p-value Pr(bootstrap_mean >= observed_mean)
    count_ge = int(np.sum(dist >= observed_mean))
    p_value = float((count_ge + 1) / (n_iter + 1))
    ci = _ci_from_distribution(dist, level=ci_level)

    return {
        "distribution": dist,
        "observed_mean": observed_mean,
        "mean": float(dist.mean()) if dist.size else 0.0,
        "std": std,
        "p_value": p_value,
        "ci": ci,
        "trials": int(n_iter),
        "method": method,
        "block_length": block_length,
        "jitter": jitter,
        "fallback": fallback,
    }


__all__ = ["hadj_bb_bootstrap"]
