"""Execution & Costs Integration (T013)

Validates reconciliation of execution cost components (slippage, spread / participation, fees)
through the execution simulator pipeline by comparing fills produced under different
ExecutionSpec configurations. Ensures deterministic adjustments and monotonic cost scaling.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from domain.execution import simulator
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def _synth_frame() -> pd.DataFrame:
    # Minimal sized frame expected by simulator: must contain timestamp, open/high/low/close, position_size, volume
    rows = []
    price = 100.0
    for i in range(10):
        o = price
        c = o * (1 + (0.001 if i % 2 == 0 else -0.0005))
        h = max(o, c) * 1.0002
        low = min(o, c) * 0.9998
        vol = 10_000 + i * 100
        # Position alternates 0 -> 1 -> 0 to force trades
        pos = 1 if i % 2 == 0 else 0
        # Simple signal: when pos transitions to 1 emit 1, when to 0 emit -1 else 0
        signal = 1 if pos == 1 else -1
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=i),
                "open": o,
                "high": h,
                "low": low,
                "close": c,
                "volume": vol,
                "position_size": pos,
                "signal": signal,
            }
        )
        price = c
    return pd.DataFrame(rows)


@pytest.mark.parametrize("slip_bps,fee_bps,spread_pct", [(5.0, 2.0, 0.001)])
def test_execution_costs_reconciliation(
    tmp_path: Path, slip_bps: float, fee_bps: float, spread_pct: float
) -> None:  # T013
    base_df = _synth_frame()
    # Base config (no extra costs)
    cfg_base = RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 2, "long_window": 4}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 1.0}),
        execution=ExecutionSpec(slippage_bps=0.0, fee_bps=0.0),
        validation=ValidationSpec(),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
    )
    fills_base, _ = simulator.simulate(cfg_base, base_df)
    assert not fills_base.empty, "Base scenario produced no fills"

    # Scenario with slippage + fees + spread model
    cfg_costs = RunConfig(
        indicators=cfg_base.indicators,
        strategy=cfg_base.strategy,
        risk=cfg_base.risk,
        execution=ExecutionSpec(
            slippage_bps=slip_bps,
            fee_bps=fee_bps,
            slippage_model={
                "model": "spread_pct",
                "params": {"spread_pct": spread_pct},
            },
        ),
        validation=ValidationSpec(),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
    )
    fills_costs, _ = simulator.simulate(cfg_costs, base_df)
    assert len(fills_costs) == len(fills_base)

    # Compare average execution price difference magnitude (should be >= 0 due to added costs on buys / reduced on sells but net effect increases absolute deviation)
    avg_base = fills_base.price.mean()
    avg_costs = fills_costs.price.mean()
    # Not a strict inequality because directional mix may offset; enforce difference exists
    assert (
        abs(avg_costs - avg_base) > 0
    ), "Cost scenario did not change average execution prices"

    # Per-fill: apply directional expectation
    merged = fills_base.assign(base_price=fills_base.price).copy()
    merged["cost_price"] = fills_costs.price.values
    # For buy fills (side==1) expect cost_price >= base_price (pay more); for sells (side==-1) cost_price <= base_price
    buys = merged[merged.side == 1]
    sells = merged[merged.side == -1]
    if not buys.empty:
        assert (buys.cost_price >= buys.base_price).all()
    if not sells.empty:
        assert (sells.cost_price <= sells.base_price).all()

    # Determinism: rerun costs scenario -> identical fills dataframe
    fills_costs_2, _ = simulator.simulate(cfg_costs, base_df)
    pd.testing.assert_frame_equal(
        fills_costs.reset_index(drop=True), fills_costs_2.reset_index(drop=True)
    )


__all__ = ["test_execution_costs_reconciliation"]
