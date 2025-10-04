from __future__ import annotations

import pandas as pd
from domain.indicators.sma import SimpleMovingAverage, dual_sma_indicator


def test_dual_sma_on_clean_dataset_duplicates_removed() -> None:
    # Build frame with duplicate timestamp and missing row to simulate what ingestion would clean
    ts = pd.date_range("2024-01-01", periods=6, freq="1D")
    # Introduce a duplicate timestamp manually
    ts_list = [*list(ts), ts[2]]
    close = [10, 11, 12, 13, 14, 15, 16]
    open_ = close
    high = [c + 0.5 for c in close]
    low = [c - 0.5 for c in close]
    volume = [100] * len(close)
    raw = pd.DataFrame(
        {
            "timestamp": ts_list,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
    # Simulate cleaning (drop duplicate keep first, drop missing none here)
    cleaned = raw.drop_duplicates(subset=["timestamp"], keep="first").reset_index(
        drop=True
    )

    out = dual_sma_indicator(cleaned, params={"short_window": 2, "long_window": 4})
    assert f"sma_short_{2}" in out.columns
    assert f"sma_long_{4}" in out.columns
    # Validate no NaN after enough periods for long window
    assert out[f"sma_long_{4}"].iloc[3] == cleaned["close"].iloc[0:4].mean()


def test_simple_sma_feature_columns_consistency() -> None:
    sma = SimpleMovingAverage(window=3)
    ts = pd.date_range("2024-01-01", periods=5, freq="1D")
    close = pd.Series([1, 2, 3, 4, 5])
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1,
        }
    )
    feats = sma.compute(df)
    col = sma.feature_columns()[0]
    assert col in feats.columns
    assert feats[col].iloc[2] == (1 + 2 + 3) / 3
