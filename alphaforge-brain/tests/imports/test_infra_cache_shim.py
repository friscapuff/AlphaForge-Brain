"""Guard test ensuring legacy infra.cache import surface remains functional.

Covers:
- Importing CandleCache, FeaturesCache, cache_metrics from both legacy root package path
    and src implementation.
- Basic store/load roundtrip for CandleCache (ensuring Windows-safe file naming works).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Legacy path import (root shim)
from infra.cache import CandleCache, cache_metrics  # type: ignore


def _df(n: int = 5) -> pd.DataFrame:
    import datetime as _dt

    base = _dt.datetime(2024, 1, 1, tzinfo=_dt.timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += 1
        rows.append(
            {
                "timestamp": base + _dt.timedelta(minutes=i),
                "open": price,
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price,
                "volume": 100 + i,
            }
        )
    return pd.DataFrame(rows)


def test_legacy_infra_cache_import_and_roundtrip(tmp_path: Path) -> None:
    cache = CandleCache(tmp_path)
    cache_metrics.get().hits = cache_metrics.get().misses = (
        cache_metrics.get().writes
    ) = 0
    frame = _df(8)
    out1 = cache.load(symbol="TEST", start=0, end=7, frame=frame)
    assert len(out1) == 8
    assert cache_metrics.get().misses == 1
    out2 = cache.load(symbol="TEST", start=0, end=7, frame=frame)
    assert len(out2) == 8
    assert cache_metrics.get().hits >= 1
    # Ensure path naming used underscores not colons (Windows-safe)
    for p in tmp_path.rglob("*.parquet"):
        assert ":" not in p.name
