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


def _candles(n: int = 240) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 75.0
    for i in range(n):
        price += (1 if i % 30 < 15 else -1) * 0.4
        rows.append({
            "timestamp": base + timedelta(minutes=i),
            "open": price,
            "high": price + 0.2,
            "low": price - 0.2,
            "close": price,
            "volume": 900 + i,
        })
    return pd.DataFrame(rows)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 18})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 5, "long_window": 18}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.15}),
        execution=ExecutionSpec(mode="sim", fee_bps=2.5, slippage_bps=2.5),
        symbol="VAL",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _pipeline() -> tuple[pd.DataFrame, pd.DataFrame]:
    import domain.indicators.sma  # noqa: F401
    cfg = _config()
    candles = _candles(400)
    signals = run_strategy(cfg, candles, candle_hash="dummyrunall")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, positions_summary = build_state(fills, positions)
    return trades, positions_summary


def test_validation_run_all_deterministic() -> None:
    trades, positions_summary = _pipeline()
    from domain.validation import run_all

    result = run_all(trades, None, seed=123, config={
        "permutation": {"n": 50},
        "block_bootstrap": {"n_iter": 60, "block_size": 5},
        "monte_carlo": {"n_iter": 40, "model": "normal", "params": {"mu": 0.0002, "sigma": 0.0003}},
        "walk_forward": {"n_folds": 5},
    })
    required_top = {"permutation", "block_bootstrap", "monte_carlo_slippage", "walk_forward", "summary", "seed"}
    assert required_top.issubset(result.keys())
    assert "p_value" in result["permutation"]
    assert "p_value" in result["block_bootstrap"]
    assert "p_value" in result["monte_carlo_slippage"]
    assert isinstance(result["walk_forward"], dict)
    # Determinism subset
    result2 = run_all(trades, None, seed=123, config={
        "permutation": {"n": 50},
        "block_bootstrap": {"n_iter": 60, "block_size": 5},
        "monte_carlo": {"n_iter": 40, "model": "normal", "params": {"mu": 0.0002, "sigma": 0.0003}},
        "walk_forward": {"n_folds": 5},
    })
    assert result["summary"] == result2["summary"]
    assert result["seed"] == result2["seed"]