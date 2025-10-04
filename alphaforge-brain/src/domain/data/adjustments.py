"""Corporate action adjustments (FR-104).

Minimal adjustment utilities to support T009-T010:
- AdjustmentPolicy: currently supports "full_adjusted" (splits + dividends placeholder) and "none".
- AdjustmentFactors: events DataFrame with columns: ts (epoch ms), split (float, optional), dividend (float, optional),
  and a coverage flag declaring completeness. We require full coverage when policy is full_adjusted.
- Stable factors digest: canonical hash over sorted event rows (ts, split, dividend) and policy string.
- apply_full_adjustments: back-adjust OHLC columns for splits using a backward cumulative factor.

Notes:
- Dividend handling is provisioned: digest accounts for dividend events; price adjustment currently applies splits only.
  This is sufficient for tests in T009 and can be extended later to total-return adjustments.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import pandas as pd

AdjustmentPolicy = Literal["none", "full_adjusted"]


@dataclass(slots=True)
class AdjustmentFactors:
    events: (
        pd.DataFrame
    )  # expected columns: ts (int ms), optional split (float), optional dividend (float)
    coverage_full: bool = True


def compute_factors_digest(
    policy: AdjustmentPolicy, factors: AdjustmentFactors | None
) -> str | None:
    """Return a stable digest of factors and policy.

    When policy is "none", returns None. For full_adjusted with empty events, returns a deterministic digest.
    """
    if policy == "none":
        return None
    if factors is None:
        raise ValueError("full_adjusted policy requires AdjustmentFactors")
    # Canonicalize events: select known columns, fill NaNs with 0.0, sort by ts asc
    ev = factors.events.copy()
    for col in ["split", "dividend"]:
        if col not in ev.columns:
            ev[col] = 0.0
    ev = ev[["ts", "split", "dividend"]].copy()
    ev = ev.fillna(0.0)
    ev = ev.sort_values("ts", kind="mergesort").reset_index(drop=True)
    # Deterministic CSV bytes
    csv_bytes = ev.to_csv(index=False, lineterminator="\n", float_format="%.8f").encode(
        "utf-8"
    )
    base = f"policy={policy}\n".encode() + csv_bytes
    return hashlib.sha256(base).hexdigest()


def _apply_split_back_adjustment(prices: pd.Series, events: pd.Series) -> pd.Series:
    """Back-adjust price series for splits using backward cumulative product.

    prices: float series (e.g., close)
    events: split factor at exact timestamps index-aligned to prices (float; 0 or 1 means no split; >1 split ratio)
    """
    # Ensure aligned index
    split_factors = events.fillna(0.0).astype(float)
    # Backward cumulative product: at each row, adjusted_price = price / cum_factor_future
    adjusted = prices.copy().astype(float)
    cum = 1.0
    # Iterate from newest to oldest
    for i in range(len(prices) - 1, -1, -1):
        # Apply current row split to cumulative first so that the event row is adjusted as well
        s = float(split_factors.iloc[i]) if i < len(split_factors) else 0.0
        if s and s > 0.0:
            cum *= s
        p = float(prices.iloc[i])
        adjusted.iloc[i] = p / cum if cum != 0.0 else float("nan")
    return adjusted


def apply_full_adjustments(
    df: pd.DataFrame, factors: AdjustmentFactors
) -> pd.DataFrame:
    """Apply full adjustments (currently splits) to OHLC columns of df.

    df must include columns: ts, open, high, low, close. Volume left unchanged.
    factors.events must include column ts (to align), optional split column (float ratio, e.g., 2.0 for 2-for-1).
    """
    if not factors.coverage_full:
        raise ValueError(
            "AdjustmentFactors coverage is partial; require full coverage for full_adjusted policy"
        )
    if df.empty:
        return df.copy()
    out = df.copy()
    # Align events to df rows by ts, forward/back fill zeros where no event matches
    ev = factors.events.copy()
    if "split" not in ev.columns:
        ev["split"] = 0.0
    # Build a per-row split series by merging on ts
    merged = pd.merge(out[["ts"]], ev[["ts", "split"]], how="left", on="ts").fillna(
        {"split": 0.0}
    )
    split_series = merged["split"].astype(float)
    # Apply split adjustments using backward cumulative factor
    for col in ["open", "high", "low", "close"]:
        out[col] = _apply_split_back_adjustment(out[col], split_series)
    # Note: volume left as-is; can be adjusted by multiplying by cumulative split if desired in future.
    return out


def incorporate_policy_into_hash(
    raw_digest: str, policy: AdjustmentPolicy, factors_digest: str | None
) -> str:
    """Combine raw digest with policy and factors digest into a final dataset hash.

    Ensures that dataset digest changes when policy or factors change, even if adjusted series equals raw numerically.
    """
    payload = (
        f"raw={raw_digest};policy={policy};factors={factors_digest or 'none'}".encode()
    )
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "AdjustmentFactors",
    "AdjustmentPolicy",
    "apply_full_adjustments",
    "compute_factors_digest",
    "incorporate_policy_into_hash",
]
