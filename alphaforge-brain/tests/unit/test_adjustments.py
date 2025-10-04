import pandas as pd
from domain.data.adjustments import (
    AdjustmentFactors,
    apply_full_adjustments,
    compute_factors_digest,
    incorporate_policy_into_hash,
)


def test_factors_digest_stable_and_policy_sensitive():
    events = pd.DataFrame(
        {
            "ts": [1000, 2000, 3000],
            "split": [0.0, 2.0, 0.0],
            "dividend": [0.0, 0.0, 0.5],
        }
    )
    f = AdjustmentFactors(events=events, coverage_full=True)
    d1 = compute_factors_digest("full_adjusted", f)
    # Reordered events should yield same digest
    f2 = AdjustmentFactors(
        events=events.sample(frac=1.0, random_state=42), coverage_full=True
    )
    d2 = compute_factors_digest("full_adjusted", f2)
    assert d1 == d2
    # Policy change changes combined dataset hash
    raw = "a" * 64
    h1 = incorporate_policy_into_hash(raw, "full_adjusted", d1)
    h2 = incorporate_policy_into_hash(raw, "none", None)
    assert h1 != h2


def test_apply_split_back_adjustment_simple_case():
    # Price series with a 2-for-1 split at t2; older prices should be halved
    df = pd.DataFrame(
        {
            "ts": [1000, 2000, 3000, 4000],
            "open": [10.0, 12.0, 14.0, 16.0],
            "high": [11.0, 13.0, 15.0, 17.0],
            "low": [9.0, 11.0, 13.0, 15.0],
            "close": [10.5, 12.5, 14.5, 16.5],
            "volume": [100, 100, 100, 100],
        }
    )
    events = pd.DataFrame({"ts": [3000], "split": [2.0]})
    f = AdjustmentFactors(events=events, coverage_full=True)
    adj = apply_full_adjustments(df, f)
    # Rows at and before split (<= 3000) are adjusted relative to future prices; using backward cumproduct
    # After split (latest point), no adjustment
    assert adj.loc[3, "close"] == df.loc[3, "close"]
    # At split timestamp (3000), price divided by 2.0
    assert abs(adj.loc[2, "close"] - df.loc[2, "close"] / 2.0) < 1e-12
    # Before split, still divided by 2.0 (single split in future)
    assert abs(adj.loc[0, "open"] - df.loc[0, "open"] / 2.0) < 1e-12
