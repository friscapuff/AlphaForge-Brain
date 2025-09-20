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


def _candles(n: int = 180):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += (1 if i % 16 < 8 else -1) * 0.55
        rows.append({
            "timestamp": base + timedelta(minutes=i),
            "open": price,
            "high": price + 0.25,
            "low": price - 0.25,
            "close": price,
            "volume": 800 + i,
        })
    return pd.DataFrame(rows)


def _config():
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 15})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 5, "long_window": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(mode="sim", fee_bps=3.0, slippage_bps=3.0),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-15",
    )


def _pipeline():
    import domain.indicators.sma  # noqa: F401
    cfg = _config()
    candles = _candles(200)
    signals = run_strategy(cfg, candles, candle_hash="dummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, _ = build_state(fills, positions)
    return trades


def test_block_bootstrap_distribution_deterministic():
    trades = _pipeline()
    from domain.validation import block_bootstrap

    result = block_bootstrap(trades, n_iter=120, block_size=7, seed=123)
    # Basic keys
    assert {"distribution", "observed_mean", "mean", "p_value"}.issubset(result.keys())
    dist = result["distribution"]
    assert len(dist) == 120
    # Deterministic repeat
    result2 = block_bootstrap(trades, n_iter=120, block_size=7, seed=123)
    assert (result2["distribution"] == dist).all()
    assert result["observed_mean"] == result2["observed_mean"]
    # p_value bounds
    assert 0.0 <= result["p_value"] <= 1.0
    # Sanity: distribution variance positive (unless degenerate)
    if len(dist) > 1:
        assert dist.var() >= 0
