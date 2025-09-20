from datetime import datetime, timedelta, timezone

import pandas as pd

from domain.execution.simulator import simulate
from domain.execution.state import build_state
from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)
from domain.strategy.runner import run_strategy


def _candles(n: int = 160):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 50.0
    for i in range(n):
        # mild trending then mean-revert pattern
        price += (1 if i % 20 < 10 else -1) * 0.35
        rows.append({
            "timestamp": base + timedelta(minutes=i),
            "open": price,
            "high": price + 0.2,
            "low": price - 0.2,
            "close": price,
            "volume": 500 + i,
        })
    return pd.DataFrame(rows)


def _config():
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 15})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 5, "long_window": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.2}),
        execution=ExecutionSpec(mode="sim", fee_bps=2.0, slippage_bps=2.0),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-05",
    )


def _pipeline():
    import domain.indicators.sma  # noqa: F401
    cfg = _config()
    candles = _candles(180)
    signals = run_strategy(cfg, candles, candle_hash="dummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, positions_df = build_state(fills, positions)
    return trades, positions_df


def test_monte_carlo_slippage_distribution_deterministic():
    trades, positions_df = _pipeline()
    from domain.validation import monte_carlo_slippage

    result = monte_carlo_slippage(trades, positions_df, n_iter=150, model="normal", params={"mu":0.0002, "sigma":0.0003}, seed=99)
    assert {"distribution", "observed_metric", "p_value"}.issubset(result.keys())
    dist = result["distribution"]
    assert len(dist) == 150
    # Deterministic repeat
    result2 = monte_carlo_slippage(trades, positions_df, n_iter=150, model="normal", params={"mu":0.0002, "sigma":0.0003}, seed=99)
    assert (result2["distribution"] == dist).all()
    assert result["observed_metric"] == result2["observed_metric"]
    assert 0.0 <= result["p_value"] <= 1.0
    # Most deltas should be negative or zero (cost stress)
    assert (dist <= 0).mean() > 0.5
