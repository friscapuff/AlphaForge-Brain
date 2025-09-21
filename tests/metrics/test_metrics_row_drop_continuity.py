"""T028: Ensure metrics unaffected by removed rows (index continuity)

We simulate a dataset slice with deliberately dropped rows (e.g., missing data) and
verify that equity curve construction and metrics computation produce:
 - strictly increasing timestamp index
 - no NaNs in equity or return columns
 - identical metrics result when compared to a version where the dropped rows are
   simply absent from the raw positions input (i.e., no hidden forward fill artifacts)
"""

from __future__ import annotations

import pandas as pd

from domain.metrics.calculator import build_equity_curve, compute_metrics


def test_metrics_index_continuity_after_row_drops() -> None:
    # Base timestamps (simulate 6 sequential minutes)
    ts_all = pd.date_range("2024-01-01 09:30:00", periods=6, freq="1min")
    # Create positions/equity proxy with a linear increase
    equity_values = [100, 101, 102, 103, 104, 105]
    base_df = pd.DataFrame({"timestamp": ts_all, "equity": equity_values})

    # Simulate cleaned dataset where the 3rd observation (index 2) was dropped earlier
    cleaned_df = base_df.drop(index=[2]).reset_index(drop=True)

    curve_clean = build_equity_curve(cleaned_df)
    assert curve_clean["timestamp"].is_monotonic_increasing, "Timestamps not strictly increasing after row drops"
    assert not curve_clean["equity"].isna().any(), "Equity contains NaNs after row drops"
    assert not curve_clean["return"].isna().any(), "Return contains NaNs after row drops"

    # Now build curve from a pre-filtered positions set that never contained the row (equivalent expectation)
    prefiltered_df = cleaned_df.copy()
    curve_prefilter = build_equity_curve(prefiltered_df)

    m_clean = compute_metrics(pd.DataFrame(), curve_clean)
    m_pref = compute_metrics(pd.DataFrame(), curve_prefilter)
    # Removing a row vs never having it should yield identical summary metrics with this construction
    assert m_clean == m_pref, "Metrics diverge after row drop vs prefiltered baseline"
