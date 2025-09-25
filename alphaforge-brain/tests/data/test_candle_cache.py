from pathlib import Path
from typing import Any

import pandas as pd

from infra.cache.candles import CandleCache
from infra.utils.hash import sha256_of_text  # added helper

# We will import cache module later after implementation


def make_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts": [1, 2, 3],
            "open": [10.0, 11.0, 12.0],
            "high": [10.5, 11.5, 12.5],
            "low": [9.5, 10.5, 11.5],
            "close": [10.2, 11.1, 12.2],
            "volume": [100, 120, 110],
        }
    )


def test_cache_round_trip_and_key(tmp_path: Path, monkeypatch: Any) -> None:
    df = make_df()

    cache = CandleCache(root=tmp_path)

    # Expected key derivation spec (symbol/start/end plus content hash)
    symbol = "TEST"
    start = 1
    end = 3
    content_hash = sha256_of_text(df.to_csv(index=False))
    expected_key_prefix = f"{symbol}:{start}:{end}:{content_hash[:12]}"

    path = cache.store(symbol=symbol, start=start, end=end, frame=df)
    assert Path(path).exists()
    loaded = cache.load(symbol=symbol, start=start, end=end, frame=df)
    pd.testing.assert_frame_equal(df, loaded)
    assert cache._last_key is not None and cache._last_key.startswith(
        expected_key_prefix
    )


def test_cache_idempotent_reuse(tmp_path: Path, monkeypatch: Any) -> None:
    df = make_df()
    writes = {"count": 0}

    # Placeholder hook to observe writes.
    def fake_write_hook() -> None:
        writes["count"] += 1

    from infra.cache.candles import CandleCache

    cache = CandleCache(root=tmp_path, on_store=fake_write_hook)
    cache.store(symbol="TEST", start=1, end=3, frame=df)
    first_writes = writes["count"]
    cache.store(symbol="TEST", start=1, end=3, frame=df)  # should reuse
    assert writes["count"] == first_writes
