from typing import Any

import pandas as pd

from domain.features.engine import build_features
from domain.indicators.registry import indicator_registry
from domain.indicators.sma import SimpleMovingAverage, dual_sma_indicator


def test_nvda_slice_indicators_end_to_end(nvda_canonical_slice: tuple[Any, Any]) -> None:
    (slice_df, meta) = nvda_canonical_slice
    # Register a simple SMA indicator instance for this test (avoid polluting global across parallel by cleanup)
    sma = SimpleMovingAverage(window=10)
    indicator_registry.register(sma)

    # Apply features
    featured = build_features(slice_df, use_cache=False)

    # Dual SMA via function registry (already available) - ensure output columns present if we call it directly
    dual_df = dual_sma_indicator(slice_df, params={"short_window":5, "long_window":20})

    # Assertions
    sma_col = sma.feature_columns()[0]
    assert sma_col in featured.columns, "Simple SMA feature missing in feature engine output"

    # Ensure no lookahead: last defined SMA value equals mean of previous window closes
    valid_rows = featured.dropna(subset=[sma_col])
    if not valid_rows.empty:
        last_idx = valid_rows.index[-1]
        window = slice_df.loc[last_idx-9:last_idx, "close"]
        assert abs(featured.loc[last_idx, sma_col] - window.mean()) < 1e-12

    # Dual SMA columns present
    assert any(c.startswith("sma_short_") for c in dual_df.columns)
    assert any(c.startswith("sma_long_") for c in dual_df.columns)

    # zero_volume passthrough: if present in slice, must be unchanged
    if "zero_volume" in slice_df.columns:
        assert "zero_volume" in featured.columns
        pd.testing.assert_series_equal(slice_df["zero_volume"], featured["zero_volume"], check_names=True)


def test_nvda_slice_requires_dataset(nvda_canonical: tuple[Any, Any]) -> None:
    # Fixture ensures dataset exists otherwise test skipped.
    df, meta = nvda_canonical
    assert len(df) >= 1
    assert meta.symbol == "NVDA"
