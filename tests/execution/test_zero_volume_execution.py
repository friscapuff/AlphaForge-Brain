import math
from typing import Any

import pandas as pd
import pytest

from domain.execution.simulator import simulate
from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


@pytest.fixture
def sized_df_with_zero_volume(nvda_canonical_slice: tuple[pd.DataFrame, Any]) -> tuple[pd.DataFrame, RunConfig]:  # returns sized frame and config
    (slice_df, meta) = nvda_canonical_slice
    df = slice_df.copy().iloc[:120]  # limit scope
    # Construct a simple alternating signal after first bar
    df["signal"] = pd.Series([math.nan] + [1, -1] * (len(df) // 2), index=df.index)[: len(df)]
    # Provide execution layer expected timestamp column (convert ms epoch -> pandas Timestamp)
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    # Force some zero-volume bars by flag
    zero_idx = df.index[::25]
    df.loc[zero_idx, "volume"] = 0
    df.loc[zero_idx, "zero_volume"] = 1

    # Apply fixed fraction risk for position sizing
    cfg = RunConfig(
        indicators=[IndicatorSpec(name="sma", params={"window": 3})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 3, "long_window": 5}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.05}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA", timeframe="1m", start="2022-01-01", end="2022-01-02",
    )
    sized = apply_risk(cfg, df, equity=20_000)
    return sized, cfg


def test_skip_zero_volume_holds_position(sized_df_with_zero_volume: tuple[pd.DataFrame, RunConfig]) -> None:
    sized, cfg = sized_df_with_zero_volume
    fills_skip, positions_skip = simulate(cfg, sized, initial_cash=50_000, skip_zero_volume=True)
    # Ensure no fills executed on zero-volume bars
    zero_ts = set(sized.loc[sized["volume"] == 0, "timestamp"].tolist())
    if not fills_skip.empty:
        assert not any(ts in zero_ts for ts in fills_skip["timestamp"].tolist())

    # Run without skipping for comparison
    fills_all, positions_all = simulate(cfg, sized, initial_cash=50_000, skip_zero_volume=False)

    # When skipping, total number of fills should be <= non-skipping mode
    assert len(fills_skip) <= len(fills_all)

    # Equity path should not diverge catastrophically; last equity within 5% if positions eventually neutralize
    if not positions_all.empty and not positions_skip.empty:
        end_all = positions_all["equity"].iloc[-1]
        end_skip = positions_skip["equity"].iloc[-1]
        assert abs(end_all - end_skip) / max(1.0, abs(end_all)) < 0.05


def test_zero_volume_bars_do_not_crash(sized_df_with_zero_volume: tuple[pd.DataFrame, RunConfig]) -> None:
    sized, cfg = sized_df_with_zero_volume
    # Should run without exceptions
    simulate(cfg, sized, initial_cash=10_000, skip_zero_volume=True)
    simulate(cfg, sized, initial_cash=10_000, skip_zero_volume=False)
