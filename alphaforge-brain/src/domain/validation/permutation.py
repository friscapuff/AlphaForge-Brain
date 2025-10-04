from __future__ import annotations

import random

import pandas as pd


def _extract_return_series(
    trades_df: pd.DataFrame, positions_df: pd.DataFrame | None
) -> pd.Series:
    """Derive per-trade returns series used for permutation.

    Preference: trade-level percentage returns if available; else fall back to equity curve returns if provided.
    trades_df expected columns: return_pct OR (pnl, entry_price, qty) to derive fallback.
    """
    if trades_df is None or trades_df.empty:
        return pd.Series([], dtype=float)
    if "return_pct" in trades_df.columns:
        s = trades_df["return_pct"].dropna().astype(float)
        return s
    # Fallback attempt
    if {"pnl", "qty", "entry_price"}.issubset(trades_df.columns):
        # approximate return = pnl / (qty * entry_price)
        base = trades_df["qty"] * trades_df["entry_price"].replace(0, pd.NA)
        returns = trades_df["pnl"] / base
        return returns.dropna().astype(float)
    return pd.Series([], dtype=float)


def permutation_test(
    trades_df: pd.DataFrame,
    positions_df: pd.DataFrame | None = None,
    *,
    n: int = 200,
    seed: int | None = None,
) -> dict[str, float | list[float]]:
    """Permutation test for mean return significance.

    Returns dict with keys: p_value, observed_mean, null_mean, null_std, samples (list of null means)
    p-value computed as fraction of null samples whose mean >= observed_mean (one-sided test for positive edge).
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    returns = _extract_return_series(trades_df, positions_df)
    if returns.empty:
        return {
            "p_value": 1.0,
            "observed_mean": 0.0,
            "null_mean": 0.0,
            "null_std": 0.0,
            "samples": [],
        }
    data = returns.to_list()
    observed_mean = float(sum(data) / len(data))
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        shuffled = data[:]  # copy
        rng.shuffle(shuffled)
        samples.append(sum(shuffled) / len(shuffled))
    import statistics

    null_mean = float(statistics.mean(samples)) if samples else 0.0
    null_std = float(statistics.pstdev(samples)) if len(samples) > 1 else 0.0
    # One-sided p-value: proportion of null >= observed
    if samples:
        count_ge = sum(1 for m in samples if m >= observed_mean)
        p_value = (count_ge + 1) / (len(samples) + 1)  # add-one smoothing
    else:
        p_value = 1.0
    return {
        "p_value": float(p_value),
        "observed_mean": observed_mean,
        "null_mean": null_mean,
        "null_std": null_std,
        "samples": samples,
    }


__all__ = ["permutation_test"]
