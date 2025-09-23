"""Permutation Validation Integration (T014)

Runs a minimal pipeline to produce trades then applies permutation_test to
assert p_value presence, bounds, determinism, and that enabling the validation
path does not mutate trades.
"""

from __future__ import annotations

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
from domain.validation.permutation import permutation_test


def _candles(n: int = 120) -> pd.DataFrame:
    base = pd.Timestamp("2024-01-01", tz="UTC")
    rows = []
    price = 100.0
    for i in range(n):
        price += (1 if i % 10 < 5 else -1) * 0.3
        rows.append({
            "timestamp": base + pd.Timedelta(minutes=i),
            "open": price,
            "high": price + 0.15,
            "low": price - 0.15,
            "close": price,
            "volume": 1_000 + i,
        })
    return pd.DataFrame(rows)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"short_window": 4, "long_window": 12})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 4, "long_window": 12}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 1.0}),
        execution=ExecutionSpec(slippage_bps=0.0, fee_bps=0.0),
        symbol="TEST", timeframe="1m", start="2024-01-01", end="2024-01-02"
    )


def _pipeline(seed: int = 123):
    import domain.indicators.sma  # noqa: F401
    cfg = _config()
    candles = _candles(150)
    signals = run_strategy(cfg, candles, candle_hash="dummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, _ = build_state(fills, positions)
    return trades, positions


def test_permutation_validation() -> None:  # T014
    trades, positions = _pipeline()
    result = permutation_test(trades, positions, n=40, seed=999)
    assert {"p_value", "observed_mean", "null_mean", "null_std", "samples"}.issubset(result.keys())
    assert 0 <= result["p_value"] <= 1
    # Determinism
    result2 = permutation_test(trades, positions, n=40, seed=999)
    assert result == result2
    # Trades unchanged by validation
    trades2, _ = _pipeline()
    assert trades.equals(trades2)

__all__ = ["test_permutation_validation"]
