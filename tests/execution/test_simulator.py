from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from domain.execution import simulator
from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)
from domain.strategy.runner import run_strategy


def _base_config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"short_window": 2, "long_window": 4})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 2, "long_window": 4}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 1.0}),
        execution=ExecutionSpec(fee_bps=5.0, slippage_bps=10.0),
        validation=ValidationSpec(),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        seed=123,
    )


def build_sized_frame(signals: list[int] | list[float], position_size: int | float = 10, start: int = 0) -> pd.DataFrame:
    # Build a DataFrame with open/close identical for simplicity
    n = len(signals) + 1  # one extra bar for final potential execution
    ts = pd.date_range("2024-01-01", periods=n, freq="1min")
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "open": np.linspace(100, 100 + n - 1, n),
            "close": np.linspace(100, 100 + n - 1, n),
            "signal": [np.nan, *signals],  # signal triggers execution on next bar
            "position_size": position_size,
            "volume": 1.0,
        }
    )
    return df


def test_t_plus_one_fill_rule() -> None:
    cfg = _base_config()
    # Single long signal at bar 1 (index 1 in sized frame after leading NaN), should fill at bar 2 open
    sized = build_sized_frame([1, 0, 0])  # signals for bars 1-3 lead to potential fills at bars 2-4
    fills, positions = simulator.simulate(cfg, sized)
    # Expect exactly one fill at timestamp sized.loc[2,'timestamp']
    assert len(fills) == 1
    expected_ts = sized.iloc[2].timestamp
    assert fills.iloc[0].timestamp == expected_ts


def test_cost_application_fee_and_slippage_direction() -> None:
    cfg = _base_config()
    sized = build_sized_frame([1, 0])  # signal followed by neutral to allow T+1 execution
    fills, _ = simulator.simulate(cfg, sized)
    assert not fills.empty, "Expected a fill due to T+1 after signal"
    fill_price = fills.iloc[0].price
    # Base open of execution bar (bar index 2) is sized.iloc[2].open (0-based)
    base_price = sized.iloc[2].open
    # Buy side should have increased price due to positive side for slippage+fees
    assert fill_price > base_price


def test_skip_zero_volume() -> None:
    cfg = _base_config()
    sized = build_sized_frame([1, 0, -1])
    # Force zero volume on execution bars to skip
    # Execution bars for signals at indices 1 and 3 are bars 2 and 4
    sized.loc[2, "volume"] = 0.0
    sized.loc[4, "volume"] = 0.0
    fills, _ = simulator.simulate(cfg, sized, skip_zero_volume=True)
    assert fills.empty, "All fills should be skipped due to zero volume"


def test_flatten_end_generates_synthetic_fill() -> None:
    cfg = _base_config()
    sized = build_sized_frame([1, 0, 0, 0])  # open long then hold
    fills, positions = simulator.simulate(cfg, sized, flatten_end=True)
    # Expect two fills: initial open and synthetic closing fill
    assert len(fills) == 2
    assert fills.iloc[-1].get("synthetic", False) is True
    assert positions.iloc[-1].position == 0.0


def test_empty_input_returns_empty_frames() -> None:
    cfg = _base_config()
    empty = pd.DataFrame(columns=["timestamp", "open", "close", "signal", "position_size"]).iloc[0:0]
    fills, pos = simulator.simulate(cfg, empty)
    assert fills.empty and pos.empty
 # Intentionally import simulator lazily inside tests after file creation


def _candles(n: int = 40) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        # deterministic sawtooth to force crossings
        price += (1 if i % 8 < 4 else -1) * 0.8
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,  # we will use next bar open for fills
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return pd.DataFrame(rows)


def _config(fast: int = 3, slow: int = 6, fee_bps: float = 5.0, slippage_bps: float = 10.0) -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": fast, "slow": slow})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": fast, "long_window": slow}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.2}),
        execution=ExecutionSpec(mode="sim", fee_bps=fee_bps, slippage_bps=slippage_bps),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _build_signals(cfg: RunConfig, df: pd.DataFrame) -> pd.DataFrame:
    import domain.indicators.sma  # noqa: F401 ensure registration
    signals = run_strategy(cfg, df, candle_hash="dummy", cache_root=None)
    sized = apply_risk(cfg, signals)
    return sized


def test_t_plus_one_fill_and_skip_last_bar_signal() -> None:
    cfg = _config()
    df = _candles(50)
    sized = _build_signals(cfg, df)
    from domain.execution import simulator
    fills_df, positions_df = simulator.simulate(cfg, sized)
    assert set(["timestamp","side","qty","price"]).issubset(fills_df.columns)
    # No fill can have timestamp equal to last candle timestamp (no next bar to execute on)
    if not fills_df.empty:
        last_ts = df.iloc[-1].timestamp
        assert last_ts not in set(fills_df["timestamp"])  # ensure last-bar signals skipped
    # Timestamps should be subset of candle timestamps beyond first row (since fills occur on next bar)
    candle_ts = set(df["timestamp"]) - {df.iloc[0].timestamp}
    assert set(fills_df["timestamp"]).issubset(candle_ts)


def test_fees_and_slippage_applied() -> None:
    cfg = _config(fee_bps=10, slippage_bps=25)
    df = _candles(60)
    sized = _build_signals(cfg, df)
    from domain.execution import simulator
    fills_df, _ = simulator.simulate(cfg, sized)
    if not fills_df.empty:
        # Effective prices should differ from raw next-bar open by fee/slippage directionally (BUY higher, SELL lower)
        candle_map = {r.timestamp: r.open for r in df.itertuples()}
        for r in fills_df.itertuples():
            raw_open = candle_map[r.timestamp]
            if r.side == "BUY":
                assert r.price > raw_open
            else:
                assert r.price < raw_open


def test_cash_and_position_evolution_deterministic() -> None:
    cfg = _config()
    df = _candles(80)
    sized = _build_signals(cfg, df)
    from domain.execution import simulator
    fills1, pos1 = simulator.simulate(cfg, sized)
    fills2, pos2 = simulator.simulate(cfg, sized)
    pd.testing.assert_frame_equal(fills1, fills2)
    pd.testing.assert_frame_equal(pos1, pos2)


def test_zero_volume_skips_fill_and_flatten_end_flag() -> None:
    cfg = _config()
    df = _candles(40)
    # Force a signal on bar 8 so execution would occur on bar 9 (which we'll zero volume) by directly editing sized later.
    from domain.execution import simulator
    sized = _build_signals(cfg, df)
    # If no signal at index 8, coerce one
    if sized.shape[0] > 10:
        sized.loc[sized.index[8], "signal"] = 1
        sized.loc[sized.index[8], "position_size"] = 10.0
        # Zero volume on next bar (execution bar)
        df.loc[df.index[9], "volume"] = 0
        sized.loc[sized.index[9], "volume"] = 0
    fills_df, _ = simulator.simulate(cfg, sized, skip_zero_volume=True)
    if sized.shape[0] > 10:
        zero_ts = df.iloc[9].timestamp
        assert zero_ts not in set(fills_df["timestamp"]), "Fill should be skipped on zero-volume bar when skip_zero_volume=True"


def test_flatten_end_realizes_final_position() -> None:
    cfg = _config()
    df = _candles(45)
    sized = _build_signals(cfg, df)
    from domain.execution import simulator
    # Ensure at least one open position remains into last bar by forcing a late signal
    last_idx = sized.index[-2]  # signal on penultimate bar executes on last, leaving position potentially open
    sized.loc[last_idx, "signal"] = 1
    sized.loc[last_idx, "position_size"] = 5.0
    fills_df_no, _ = simulator.simulate(cfg, sized)
    fills_df_yes, _ = simulator.simulate(cfg, sized, flatten_end=True)
    if not fills_df_no.empty and not fills_df_yes.empty:
        # Either an extra synthetic fill or a fill marked synthetic at last timestamp
        if len(fills_df_yes) == len(fills_df_no):
            # then last row should be synthetic
            assert fills_df_yes.iloc[-1].get("synthetic", False) is True
        else:
            assert len(fills_df_yes) == len(fills_df_no) + 1
