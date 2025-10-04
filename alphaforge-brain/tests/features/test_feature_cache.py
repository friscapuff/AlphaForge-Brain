from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from domain.indicators.registry import indicator_registry
from domain.indicators.sma import SimpleMovingAverage

from infra.utils.hash import sha256_of_text

# The FeaturesCache will be implemented in infra/cache/features.py with an API similar to CandleCache:
#   cache = FeaturesCache(root: Path)
#   df = cache.load_or_build(candle_df, indicators, build_fn, engine_version="v1")
# Key requirements tested:
#  - First call builds & writes parquet; second identical call reads without rewrite (we detect via mtime)
#  - Cache key depends on candle cache hash (simulate by hashing candle df text) + sorted indicator signatures + engine_version
#  - Corrupted file triggers rebuild
#  - Deterministic, Windows-safe filename


@pytest.fixture()
def tmp_cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "feature_cache"
    d.mkdir()
    return d


@pytest.fixture()
def candles_df() -> pd.DataFrame:
    data = {
        "timestamp": [
            datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 0, 3, tzinfo=timezone.utc),
        ],
        "open": [100, 101, 102, 103],
        "high": [101, 102, 103, 104],
        "low": [99, 100, 101, 102],
        "close": [100.5, 101.5, 102.5, 103.5],
        "volume": [10, 11, 12, 13],
    }
    return pd.DataFrame(data)


def _simulate_candle_hash(df: pd.DataFrame) -> str:
    text: str = df.to_csv(index=False)
    digest: str = sha256_of_text(text)
    return digest[:16]


def _indicator_signature(ind: Any) -> str:
    parts: list[str] = [getattr(ind, "name", ind.__class__.__name__)]
    window = getattr(ind, "window", None)
    if isinstance(window, int):
        parts.append(f"window={window}")
    return ":".join(parts)


def test_feature_cache_write_then_hit(
    tmp_cache_dir: Path, candles_df: pd.DataFrame
) -> None:
    indicator_registry.clear()
    ind = SimpleMovingAverage(window=3)
    indicator_registry.register(ind)

    # Lazy import until after indicators registered
    from infra.cache import features as feature_cache_mod

    cache = feature_cache_mod.FeaturesCache(tmp_cache_dir)

    candle_hash = _simulate_candle_hash(candles_df)
    indicators = list(indicator_registry.list())

    def builder(df: pd.DataFrame) -> pd.DataFrame:
        # produce feature DataFrame (same shape) using feature engine to ensure integration
        from domain.features import engine

        return engine.build_features(df)

    df1 = cache.load_or_build(
        candles_df.copy(),
        indicators,
        builder,
        candle_hash=candle_hash,
        engine_version="v1",
    )
    assert any(c.startswith("SMA_3_close") for c in df1.columns)

    # Capture modified time
    files = list(tmp_cache_dir.glob("*.parquet"))
    assert len(files) == 1
    fp = files[0]
    mtime1 = fp.stat().st_mtime

    df2 = cache.load_or_build(
        candles_df.copy(),
        indicators,
        builder,
        candle_hash=candle_hash,
        engine_version="v1",
    )
    mtime2 = fp.stat().st_mtime
    pd.testing.assert_frame_equal(df1, df2)
    assert mtime2 == mtime1, "Second call should use cached file (no rewrite)"


def test_feature_cache_corruption_rebuild(
    tmp_cache_dir: Path, candles_df: pd.DataFrame
) -> None:
    indicator_registry.clear()
    ind = SimpleMovingAverage(window=4)
    indicator_registry.register(ind)
    from infra.cache import features as feature_cache_mod

    cache = feature_cache_mod.FeaturesCache(tmp_cache_dir)

    candle_hash = _simulate_candle_hash(candles_df)
    indicators = list(indicator_registry.list())

    def builder(df: pd.DataFrame) -> pd.DataFrame:
        from domain.features import engine

        return engine.build_features(df)

    df1 = cache.load_or_build(
        candles_df.copy(),
        indicators,
        builder,
        candle_hash=candle_hash,
        engine_version="engine-v1",
    )
    files = list(tmp_cache_dir.glob("*.parquet"))
    assert files, "Cache file should exist after first build"
    fp = files[0]

    # Corrupt file (truncate)
    with open(fp, "wb") as f:
        f.write(b"corrupt")

    df2 = cache.load_or_build(
        candles_df.copy(),
        indicators,
        builder,
        candle_hash=candle_hash,
        engine_version="engine-v1",
    )
    # Should rebuild -> file size larger than corruption
    assert fp.stat().st_size > len(b"corrupt")
    pd.testing.assert_frame_equal(df1, df2)


def test_feature_cache_deterministic_filename(
    tmp_cache_dir: Path, candles_df: pd.DataFrame
) -> None:
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(window=5))
    indicator_registry.register(SimpleMovingAverage(window=2))
    from infra.cache import features as feature_cache_mod

    cache = feature_cache_mod.FeaturesCache(tmp_cache_dir)

    candle_hash = _simulate_candle_hash(candles_df)
    indicators = list(indicator_registry.list())

    def builder(df: pd.DataFrame) -> pd.DataFrame:
        from domain.features import engine

        return engine.build_features(df)

    df = cache.load_or_build(
        candles_df.copy(),
        indicators,
        builder,
        candle_hash=candle_hash,
        engine_version="verX",
    )
    assert not df.empty

    files = list(tmp_cache_dir.glob("*.parquet"))
    assert len(files) == 1
    fname = files[0].name

    # Build expected key components (sorted indicator signatures)
    sigs = sorted(_indicator_signature(i) for i in indicators)
    base = f"{candle_hash}_" + sha256_of_text("|".join(sigs) + "|verX")[:16]
    assert fname.startswith(base), f"Filename {fname} should start with {base}"
    assert ":" not in fname and "/" not in fname and "\\" not in fname
