from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from domain.data.registry import provider_registry
from infra.cache.metrics import cache_metrics

# Contract for get_candles_slice (to be implemented in domain/data/slice.py):
# get_candles_slice(symbol: str, start: datetime, end: datetime, *, provider: str, cache_dir: Path, use_cache: bool = True) -> DataFrame
# Requirements:
#  - Inclusive start/end filter
#  - Ascending timestamp (tz-aware) ordering
#  - Uses provider + CandleCache (subsequent identical call should yield candle cache hit without re-loading provider raw data)
#  - Empty DataFrame when window outside available data range
#  - In-process memoization prevents duplicate provider access in same process for identical (symbol,start,end,provider) within test

class DummyProvider:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.load_calls = 0

    def load(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:  # signature compatibility
        self.load_calls += 1
        return self.df


def _make_df() -> pd.DataFrame:
    base = datetime(2024,1,1,0,0,tzinfo=timezone.utc)
    rows = []
    for i in range(10):
        ts = base + timedelta(minutes=i)
        rows.append({
            "timestamp": ts,
            "open": 100+i,
            "high": 100.5+i,
            "low": 99.5+i,
            "close": 100.2+i,
            "volume": 1000+i,
        })
    return pd.DataFrame(rows)

@pytest.fixture()
def raw_df() -> pd.DataFrame:
    return _make_df()

@pytest.fixture()
def provider(raw_df: pd.DataFrame) -> DummyProvider:
    p = DummyProvider(raw_df)
    provider_registry.register("dummy", p)
    return p

@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "candle_cache"
    d.mkdir()
    return d


def test_slice_basic_window(provider: DummyProvider, raw_df: pd.DataFrame, cache_dir: Path) -> None:
    from domain.data import slice as slice_mod  # deferred import
    start = raw_df.loc[2, "timestamp"]
    end = raw_df.loc[5, "timestamp"]
    out = slice_mod.get_candles_slice(
        symbol="TEST",
        start=start,
        end=end,
        provider="dummy",
        cache_dir=cache_dir,
    )
    assert not out.empty
    assert out["timestamp"].min() == start
    assert out["timestamp"].max() == end
    assert list(out["timestamp"]) == sorted(out["timestamp"])  # ascending


def test_slice_cache_reuse(provider: DummyProvider, raw_df: pd.DataFrame, cache_dir: Path) -> None:
    from domain.data import slice as slice_mod
    start = raw_df.loc[0, "timestamp"]
    end = raw_df.loc[3, "timestamp"]

    # Reset metrics snapshot baseline
    baseline_hits = cache_metrics.get().hits

    out1 = slice_mod.get_candles_slice("TEST", start, end, provider="dummy", cache_dir=cache_dir)
    out2 = slice_mod.get_candles_slice("TEST", start, end, provider="dummy", cache_dir=cache_dir)

    assert provider.load_calls == 1, "Provider raw load should happen once due to cache + memoization"
    assert cache_metrics.get().hits >= baseline_hits + 1, "Expected at least one cache hit on second call"
    pd.testing.assert_frame_equal(out1, out2)


def test_slice_out_of_range_returns_empty(provider: DummyProvider, raw_df: pd.DataFrame, cache_dir: Path) -> None:
    from domain.data import slice as slice_mod
    start = raw_df["timestamp"].max() + timedelta(minutes=10)
    end = start + timedelta(minutes=5)
    out = slice_mod.get_candles_slice("TEST", start, end, provider="dummy", cache_dir=cache_dir)
    assert out.empty


def test_slice_memoization(provider: DummyProvider, raw_df: pd.DataFrame, cache_dir: Path) -> None:
    from domain.data import slice as slice_mod
    start = raw_df.loc[1, "timestamp"]
    end = raw_df.loc[4, "timestamp"]

    slice_mod.get_candles_slice("TEST", start, end, provider="dummy", cache_dir=cache_dir)
    slice_mod.get_candles_slice("TEST", start, end, provider="dummy", cache_dir=cache_dir)

    assert provider.load_calls == 1, "Memoization should prevent second provider load in-process"
