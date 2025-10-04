from __future__ import annotations

import numpy as np
import pandas as pd
from src.domain.features.engine import FeatureEngine
from src.domain.indicators.registry import IndicatorRegistry, indicator_registry
from src.domain.indicators.sma import SimpleMovingAverage
from src.services.chunking import (
    compute_required_overlap,
    compute_required_overlap_for_functions,
    iter_chunk_slices,
)


def test_iter_chunk_slices_basic_and_edges() -> None:
    # Empty
    assert list(iter_chunk_slices(0, 10)) == []
    # Monolithic due to size
    assert list(iter_chunk_slices(5, 10)) == [(0, 5, 0)]
    # Simple split without overlap
    assert list(iter_chunk_slices(10, 4, 0)) == [(0, 4, 0), (4, 8, 0), (8, 10, 0)]
    # With overlap of 2
    slices = list(iter_chunk_slices(10, 4, 2))
    assert slices == [(0, 4, 0), (2, 8, 2), (6, 10, 2)]
    # Negative overlap clamped to 0
    assert list(iter_chunk_slices(10, 4, -3)) == [(0, 4, 0), (4, 8, 0), (8, 10, 0)]


def _make_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    ts = pd.RangeIndex(n)
    close = np.cumsum(rng.normal(0, 1, size=n)) + 100
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "open": close - 0.5,
            "high": close + 0.5,
            "low": close - 1.0,
            "close": close,
            "volume": 1.0,
            "zero_volume": 0,
        },
        index=ts,
    )
    return df


def test_feature_engine_chunked_equals_monolithic_single_window() -> None:
    df = _make_df(300)
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(10))
    eng = FeatureEngine()

    mono = eng.build_features(df)
    # Compute effective overlap including function-style indicators (e.g., dual_sma)
    fn_map = IndicatorRegistry.list()
    eff_overlap = compute_required_overlap([SimpleMovingAverage(10)])
    eff_overlap = max(
        eff_overlap,
        compute_required_overlap_for_functions(
            fn_map, df.iloc[:200], FeatureEngine.base_columns
        ),
    )
    chunked = eng.build_features_chunked(df, chunk_size=57, overlap=eff_overlap)
    pd.testing.assert_frame_equal(mono, chunked)


def test_feature_engine_chunked_multi_window_overlap() -> None:
    df = _make_df(250)
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(5))
    indicator_registry.register(SimpleMovingAverage(21))
    eng = FeatureEngine()

    mono = eng.build_features(df)
    # Effective overlap includes function indicators (e.g., dual_sma long=50 -> 49)
    fn_map = IndicatorRegistry.list()
    eff_overlap = compute_required_overlap(
        [SimpleMovingAverage(5), SimpleMovingAverage(21)]
    )
    eff_overlap = max(
        eff_overlap,
        compute_required_overlap_for_functions(
            fn_map, df.iloc[:200], FeatureEngine.base_columns
        ),
    )
    chunked = eng.build_features_chunked(df, chunk_size=41, overlap=eff_overlap)
    pd.testing.assert_frame_equal(mono, chunked)


def test_compute_required_overlap_multi_window() -> None:
    indicator_registry.clear()
    sma5 = SimpleMovingAverage(5)
    sma21 = SimpleMovingAverage(21)
    ov = compute_required_overlap([sma5, sma21])
    assert ov == 20
