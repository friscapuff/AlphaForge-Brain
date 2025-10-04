from __future__ import annotations

import pandas as pd
from domain.strategy import buy_hold  # noqa: F401 ensure registration
from domain.strategy.base import StrategyRegistry


def test_buy_hold_registered_and_constant_signal():
    strat = StrategyRegistry.get("buy_hold")
    # synthetic candle frame with expected columns
    ts = pd.date_range("2024-01-01", periods=5, freq="1min", tz="UTC")
    # Convert to epoch ms (int64) matching production usage
    epoch_ms = (ts.view("int64") // 10**6).astype("int64")
    df = pd.DataFrame(
        {
            "ts": epoch_ms,
            "open": [100, 101, 102, 103, 104],
            "high": [101, 102, 103, 104, 105],
            "low": [99, 100, 101, 102, 103],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1000, 1100, 1200, 1300, 1400],
        }
    )
    out = strat(df, params={})
    # Required columns
    for col in ["timestamp", "open", "high", "low", "close", "volume", "signal"]:
        assert col in out.columns, f"missing column {col}"
    assert len(out) == len(df)
    # All signals are +1
    assert set(out.signal.unique().tolist()) == {1}


def test_buy_hold_empty_df():
    strat = StrategyRegistry.get("buy_hold")
    import pandas as pd

    empty = pd.DataFrame(
        columns=["ts", "open", "high", "low", "close", "volume"]
    )  # empty
    out = strat(empty, params={})
    assert out.empty
    # columns still present
    for col in ["timestamp", "open", "high", "low", "close", "volume", "signal"]:
        assert col in out.columns
