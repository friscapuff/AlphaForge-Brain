from __future__ import annotations

import numpy as np
import pandas as pd


def extract_returns(trades_df: pd.DataFrame, positions_df: pd.DataFrame | None = None) -> pd.Series:
    """Extract per-trade return series with fallbacks.

    Priority order:
    1. Column 'return_pct'
    2. Derive from pnl / (qty * entry_price)
    3. If positions_df provided and has 'equity', compute pct change
    Returns empty series if nothing usable.
    """
    if trades_df is not None and not trades_df.empty:
        if "return_pct" in trades_df.columns:
            s = trades_df["return_pct"].dropna().astype(float)
            if not s.empty:
                return s.reset_index(drop=True)
        if {"pnl", "qty", "entry_price"}.issubset(trades_df.columns):
            denom = (trades_df["qty"] * trades_df["entry_price"]).replace(0, pd.NA)
            s = (trades_df["pnl"] / denom).dropna().astype(float)
            if not s.empty:
                return s.reset_index(drop=True)
    if positions_df is not None and not positions_df.empty and "equity" in positions_df.columns:
        eq = positions_df["equity"].astype(float)
        rets = eq.pct_change().dropna()
        if not rets.empty:
            return rets.reset_index(drop=True)
    return pd.Series([], dtype=float)


def sample_block_indices(n_obs: int, block_size: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    """Sample block (start,end) index pairs covering ~n_obs observations.

    Uses non-overlapping sequential fill: repeatedly sample a random start; if block exceeds length, wrap by resampling.
    Stops when cumulative length >= n_obs. End index is exclusive.
    """
    if n_obs <= 0:
        return []
    block_size = max(1, block_size)
    blocks: list[tuple[int, int]] = []
    covered = 0
    while covered < n_obs:
        start = int(rng.integers(0, max(1, n_obs - block_size + 1)))
        end = start + block_size
        blocks.append((start, end))
        covered += block_size
    return blocks


__all__ = ["extract_returns", "sample_block_indices"]
