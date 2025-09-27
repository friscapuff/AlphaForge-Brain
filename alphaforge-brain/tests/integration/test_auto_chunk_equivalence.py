from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.domain.features.engine import build_features, build_features_auto_chunk
from src.domain.indicators.sma import SimpleMovingAverage, indicator_registry


def _make_df(n=8000):
    idx = pd.date_range("2024-01-01", periods=n, freq="1min")
    df = pd.DataFrame(
        {
            "timestamp": idx,
            "open": np.linspace(100, 200, n),
            "high": np.linspace(101, 201, n),
            "low": np.linspace(99, 199, n),
            "close": np.linspace(100, 200, n) + np.sin(np.arange(n) / 25.0),
            "volume": np.random.RandomState(0).randint(100, 1000, size=n),
            "zero_volume": np.zeros(n, dtype=bool),
        }
    )
    return df


@pytest.mark.integration
@pytest.mark.determinism
def test_auto_chunk_equivalence_sma():
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(10))
    indicator_registry.register(SimpleMovingAverage(50))

    df = _make_df(8000)

    mono = build_features(df, use_cache=False)
    auto = build_features_auto_chunk(df, target_chunk_mb=1)  # small to force chunking

    pd.testing.assert_frame_equal(
        mono, auto, check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12
    )
