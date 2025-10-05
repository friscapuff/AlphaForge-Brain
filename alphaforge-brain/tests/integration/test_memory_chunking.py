from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.domain.features.engine import build_features
from src.domain.indicators.sma import SimpleMovingAverage, indicator_registry


@pytest.mark.integration
@pytest.mark.memory
def test_memory_ceiling_chunking(rss_sampler):
    # Skip if RSS not supported
    if rss_sampler.rss_mb() is None:
        pytest.skip("RSS sampling not supported on this platform")

    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(200))

    n = 2_000_000  # 2 million rows (CI cap per task spec)
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1s"),
            "open": np.linspace(100, 200, n),
            "high": np.linspace(101, 201, n),
            "low": np.linspace(99, 199, n),
            "close": np.linspace(100, 200, n),
            "volume": np.ones(n),
            "zero_volume": np.zeros(n, dtype=bool),
        }
    )

    # Choose a chunk size likely below 256MB budget
    chunked = build_features(df, use_cache=False, chunk_size=200_000, overlap=199)
    assert len(chunked) == n

    # Memory ceiling expectations per spec:
    rss = rss_sampler.rss_mb()
    assert rss is None or rss < 1500  # CI cap ~1.5 GB; env-dependent
