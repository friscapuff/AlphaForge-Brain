from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from src.domain.features.engine import build_features
from src.domain.indicators.registry import indicator_registry
from src.domain.indicators.sma import SimpleMovingAverage


def _df(n: int) -> pd.DataFrame:
    ts = pd.RangeIndex(n)
    rng = np.random.default_rng(123)
    close = np.cumsum(rng.standard_normal(n)) + 50
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": close - 0.2,
            "high": close + 0.3,
            "low": close - 0.6,
            "close": close,
            "volume": 100,
            "zero_volume": 0,
        },
        index=ts,
    )


def test_build_features_chunk_mode_equals_monolithic_and_cache(tmp_path: Path) -> None:
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(7))
    indicator_registry.register(SimpleMovingAverage(19))
    df = _df(400)

    # No cache, monolithic
    mono = build_features(df, use_cache=False)
    # No cache, chunked
    # Rely on automatic overlap computation
    chunk = build_features(df, use_cache=False, chunk_size=64)
    pd.testing.assert_frame_equal(mono, chunk)

    # With cache enabled: ensure both modes hit the same cache artifact and round-trip equal
    cache_root = tmp_path / "cache"
    candle_hash = "abc123def4567890"
    # First build creates cache
    cached1 = build_features(
        df,
        use_cache=True,
        candle_hash=candle_hash,
        cache_root=cache_root,
        engine_version="v1",
        chunk_size=64,
    )
    # Second build (monolithic) should load same file -> equal
    cached2 = build_features(
        df,
        use_cache=True,
        candle_hash=candle_hash,
        cache_root=cache_root,
        engine_version="v1",
    )
    pd.testing.assert_frame_equal(cached1, cached2)
