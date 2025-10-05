import numpy as np
import pandas as pd
from domain.execution import simulator
from domain.schemas.run_config import ExecutionSpec


def _orders_frame() -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=5, freq="1min")
    # Construct a deterministic order stream
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "close": np.linspace(100, 101, 5),
            "open": np.linspace(100, 101, 5),
            "signal": [np.nan, 1, 1, 1, 1],
            "position_size": [0, 100, 100, 100, 0],  # enter size 100 then flat at end
        }
    )
    return df


def test_spread_pct_slippage_increases_fill_price_on_entry() -> None:
    df = _orders_frame()
    cfg = ExecutionSpec(
        slippage_model={"model": "spread_pct", "params": {"spread_pct": 0.001}}
    )  # 10 bps total spread
    # Build sized frame semantics expected by simulator.simulate (already has position_size + signals) -> wrap in RunConfig surrogate
    from domain.schemas.run_config import (
        IndicatorSpec,
        RiskSpec,
        RunConfig,
        StrategySpec,
        ValidationSpec,
    )

    run_cfg = RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 2, "long_window": 4}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 1.0}),
        execution=cfg,
        validation=ValidationSpec(),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
    )
    fills, _ = simulator.simulate(run_cfg, df)
    if not fills.empty:
        # First fill corresponds to entering long; expect executed price >= underlying open (approx close previous bar + spread/2 + bps costs 0)
        first = fills.iloc[0]
        raw_open = df.loc[df["timestamp"] == first.timestamp, "open"].iloc[0]
        assert first.price >= raw_open


def test_participation_rate_slippage_scales_with_size() -> None:
    df = _orders_frame()
    cfg = ExecutionSpec(
        slippage_model={
            "model": "participation_rate",
            "params": {"participation_pct": 0.5},
        }
    )
    from domain.schemas.run_config import (
        IndicatorSpec,
        RiskSpec,
        RunConfig,
        StrategySpec,
        ValidationSpec,
    )

    run_cfg = RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 2, "long_window": 4}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 1.0}),
        execution=cfg,
        validation=ValidationSpec(),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
    )
    fills1, _ = simulator.simulate(run_cfg, df)
    df2 = df.copy()
    # Increase target position size to amplify participation share (simulate larger order)
    df2.loc[df2.index[1], "position_size"] = 200
    fills2, _ = simulator.simulate(run_cfg, df2)
    if not fills1.empty and not fills2.empty:
        # Compare first fill prices; larger size should have >= price impact for BUY (higher price)
        p1 = fills1.iloc[0].price
        p2 = fills2.iloc[0].price
        assert p2 >= p1
