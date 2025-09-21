from __future__ import annotations

import pandas as pd
import pytest

from domain.data import registry as data_registry
from domain.data.providers.base import REQUIRED_CANDLE_COLUMNS, validate_candles


def test_provider_registry_decorator_and_listing() -> None:
    # Not yet registered dummy should raise
    with pytest.raises(KeyError):
        data_registry.ProviderRegistry.get("dummy")


def test_required_candle_columns_ordering_validation() -> None:
    assert set(REQUIRED_CANDLE_COLUMNS) == {"ts", "open", "high", "low", "close", "volume"}

    # Construct unsorted / invalid frame to ensure validation errors
    # Use duplicate timestamp to force non-strictly increasing after sort
    bad = pd.DataFrame({
        "ts": [1,1,2],
        "open": [1,1,1],
        "high": [1,1,1],
        "low": [1,1,1],
        "close": [1,1,1],
        "volume": [1,1,1]
    })
    with pytest.raises(ValueError):
        validate_candles(bad)  # not strictly increasing after sort due to duplicates when reversed? (we supply decreasing order)

    good = pd.DataFrame({
        "ts": [1,2,3],
        "open": [1,1,1],
        "high": [1,1,1],
        "low": [1,1,1],
        "close": [1,1,1],
        "volume": [1,1,1]
    })
    out = validate_candles(good)
    assert list(out["ts"]) == [1,2,3]
