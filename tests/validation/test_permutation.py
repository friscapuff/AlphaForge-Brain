from datetime import datetime, timedelta, timezone
from typing import Any

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


def _candles(n: int = 120) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += (1 if i % 14 < 7 else -1) * 0.5
        rows.append({
            "timestamp": base + timedelta(minutes=i),
            "open": price,
            "high": price + 0.25,
            "low": price - 0.25,
            "close": price,
            "volume": 900 + i,
        })
    return pd.DataFrame(rows)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 4, "slow": 10})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 4, "long_window": 10}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.12}),
        execution=ExecutionSpec(mode="sim", fee_bps=4.0, slippage_bps=4.0),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _pipeline() -> tuple[Any, Any]:
    import domain.indicators.sma  # noqa: F401
    cfg = _config()
    candles = _candles(160)
    signals = run_strategy(cfg, candles, candle_hash="dummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, _ = build_state(fills, positions)
    return trades, positions


def test_permutation_p_value_and_determinism() -> None:
    trades, positions = _pipeline()
    from domain.validation import permutation
    result = permutation.permutation_test(trades_df=trades, positions_df=positions, n=50, seed=123)
    assert {"p_value","observed_mean","null_mean","null_std","samples"}.issubset(result.keys())
    assert 0 <= result["p_value"] <= 1
    # Determinism
    result2 = permutation.permutation_test(trades_df=trades, positions_df=positions, n=50, seed=123)
    assert result == result2
