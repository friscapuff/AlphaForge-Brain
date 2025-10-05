import math
from datetime import datetime, timezone
from typing import TypedDict

import pandas as pd
import pytest
from domain.data.ingest_nvda import DatasetMetadata
from domain.indicators.sma import dual_sma_indicator
from domain.schemas.run_config import (
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)
from domain.strategy.base import StrategyRegistry
from domain.strategy.runner import run_strategy


class SliceMeta(TypedDict):
    symbol: str
    timeframe: str


def test_dual_sma_strategy_on_nvda_slice(
    nvda_canonical_slice: tuple[pd.DataFrame, DatasetMetadata],
) -> None:
    """T023: Ensure dual_sma strategy semantics unchanged on NVDA canonical slice.

    Validates:
      - run_strategy produces expected SMA columns & signal column
      - Signal values limited to {-1,0,1} (ignoring NaN warmup)
      - No non-null signals before long SMA warmup complete
      - Crossing logic local (no lookahead) by verifying conditions at each signal index
      - run_strategy signal identical to direct strategy invocation on precomputed features
    """
    (slice_df, meta) = nvda_canonical_slice
    assert not slice_df.empty, "Slice must be non-empty"

    fast = 5
    slow = 20

    # Build RunConfig (risk required by model but not used here for sizing yet)
    first_date = (
        datetime.fromtimestamp(int(slice_df.ts.iloc[0]) / 1000, tz=timezone.utc)
        .date()
        .isoformat()
    )
    last_date = (
        datetime.fromtimestamp(int(slice_df.ts.iloc[-1]) / 1000, tz=timezone.utc)
        .date()
        .isoformat()
    )
    cfg = RunConfig(
        indicators=[
            IndicatorSpec(name="dual_sma", params={"fast": fast, "slow": slow})
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": fast, "slow": slow}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        symbol=meta.symbol,
        timeframe=meta.timeframe,
        start=first_date,
        end=last_date,
    )

    strat_df = run_strategy(cfg, slice_df)

    short_col = f"sma_short_{fast}"
    long_col = f"sma_long_{slow}"
    assert (
        short_col in strat_df.columns
    ), "Short SMA column missing from strategy output"
    assert long_col in strat_df.columns, "Long SMA column missing from strategy output"
    assert "signal" in strat_df.columns, "Signal column missing from strategy output"

    # Allowed signal domain
    non_null_signals = strat_df["signal"].dropna()
    assert set(non_null_signals.unique()).issubset({-1, 0, 1})

    # No signals before long SMA valid
    long_valid_start = slow - 1  # first index where long rolling window full (0-based)
    early_signals = strat_df.iloc[:long_valid_start]["signal"].dropna()
    assert (
        early_signals.isna() | (early_signals == 0)
    ).all(), "Signals emitted before long SMA warmup complete"

    # Validate crossing logic locally (no lookahead). For each non-zero signal index i, check condition using i and i-1 only.
    short_series = strat_df[short_col]
    long_series = strat_df[long_col]
    for i, sig in strat_df["signal"].items():
        if math.isnan(sig) or sig == 0:
            continue
        s_val = short_series.iloc[i]
        l_val = long_series.iloc[i]
        if math.isnan(s_val) or math.isnan(l_val):
            # Shouldn't happen because we filtered NaNs -> treat as failure
            pytest.fail("Non-zero signal on NaN SMA values")
        # Previous values (may be NaN during warmup)
        if i == 0:
            prev_short = math.nan
            prev_long = math.nan
        else:
            prev_short = short_series.iloc[i - 1]
            prev_long = long_series.iloc[i - 1]
        if sig == 1:
            assert s_val > l_val, "Long signal without short>long at same bar"
            if not (math.isnan(prev_short) or math.isnan(prev_long)):
                assert not (
                    prev_short > prev_long
                ), "Long signal not at crossover (short already above long previous bar)"
        elif sig == -1:
            assert s_val < l_val, "Short signal without short<long at same bar"
            if not (math.isnan(prev_short) or math.isnan(prev_long)):
                assert not (
                    prev_short < prev_long
                ), "Short signal not at crossover (short already below long previous bar)"

    # Compare with direct strategy invocation (manual feature prep)
    features = dual_sma_indicator(slice_df, {"short_window": fast, "long_window": slow})
    direct_df = StrategyRegistry.get("dual_sma")(
        features, {"short_window": fast, "long_window": slow}
    )
    # Align indexes (run_strategy may have copied) then compare signals
    pd.testing.assert_series_equal(
        strat_df["signal"].reset_index(drop=True),
        direct_df["signal"].reset_index(drop=True),
        check_names=False,
    )

    # Determinism: rerun and compare identical
    strat_df2 = run_strategy(cfg, slice_df)
    pd.testing.assert_series_equal(
        strat_df["signal"].reset_index(drop=True),
        strat_df2["signal"].reset_index(drop=True),
        check_names=False,
    )
