from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from infra.cache.candles import CandleCache
from infra.cache.metrics import cache_metrics


def _candles_df(n: int = 5) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += 1
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price,
                "volume": 100 + i,
            }
        )
    return pd.DataFrame(rows)


def test_candle_cache_metrics_tmpdir(tmp_path: Path) -> None:
    cache_root = Path(tmp_path)
    cache = CandleCache(cache_root)

    # Reset metrics counters (direct attribute access for test visibility)
    # Reset via internal metrics object
    cache_metrics.get().hits = 0
    cache_metrics.get().misses = 0
    cache_metrics.get().writes = 0

    df = _candles_df(10)
    # key variable unused; removed per ruff F841

    # Build first time (miss expected)
    # First load should miss and write
    out1 = cache.load(symbol="TEST", start=0, end=9, frame=df)
    assert len(out1) == 10
    assert cache_metrics.get().misses == 1
    # Second identical load should hit
    out2 = cache.load(symbol="TEST", start=0, end=9, frame=df)
    assert len(out2) == 10
    assert cache_metrics.get().hits >= 1
    # Force a store with same content (should count as hit due to existing file)
    cache.store(symbol="TEST", start=0, end=9, frame=df)
    assert cache_metrics.get().hits >= 2 or cache_metrics.get().writes >= 2
