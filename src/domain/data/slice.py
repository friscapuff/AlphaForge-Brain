from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from infra.cache.candles import CandleCache

from .registry import ProviderRegistry, provider_registry

# Simple in-process memo: key -> DataFrame
_MEMO: dict[tuple[str, int, int, str], pd.DataFrame] = {}


def _dt_to_epoch(dt: datetime) -> int:
    # Assume tz-aware; fallback naive treated as UTC
    if dt.tzinfo is None:
        return int(dt.timestamp())
    return int(dt.timestamp())


def get_candles_slice(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    provider: str,
    cache_dir: Path,
    use_cache: bool = True,
) -> pd.DataFrame:
    if end < start:
        raise ValueError("end must be >= start")

    start_epoch = _dt_to_epoch(start)
    end_epoch = _dt_to_epoch(end)
    memo_key = (symbol, start_epoch, end_epoch, provider)
    # We still want cache hit accounting even if memoized; defer early return until after potential cache usage.
    memoized = _MEMO.get(memo_key)

    if memoized is None:
        # Load full raw frame from provider only first time
        try:
            prov_obj = provider_registry.get(provider)
        except Exception:
            prov_obj = ProviderRegistry.get(provider)
        raw = prov_obj.load(symbol=symbol, start=None, end=None) if hasattr(prov_obj, "load") else prov_obj(symbol=symbol, start=None, end=None)
        if "timestamp" not in raw.columns:
            raise ValueError("provider data must include timestamp column")
        window = raw[(raw["timestamp"] >= start) & (raw["timestamp"] <= end)].copy()
        window.sort_values("timestamp", inplace=True)
        window.reset_index(drop=True, inplace=True)
    else:
        window = memoized.copy()

    if use_cache:
        cache = CandleCache(cache_dir)
        cache.load(symbol=symbol, start=start_epoch, end=end_epoch, frame=window)

    if memoized is not None:
        memo_copy = memoized.copy()
        assert isinstance(memo_copy, pd.DataFrame)
        return memo_copy

    _MEMO[memo_key] = window.copy()
    assert isinstance(window, pd.DataFrame)
    return window

__all__ = ["get_candles_slice"]
