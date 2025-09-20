from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from domain.execution.simulator import simulate
from domain.execution.state import build_state
from domain.metrics.calculator import build_equity_curve, compute_metrics
from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)
from domain.strategy.runner import run_strategy


def test_build_equity_curve_and_returns():
    ts = pd.date_range("2024-01-01", periods=5, freq="1h")
    equity = [100.0, 101.0, 99.0, 102.0, 102.0]
    positions = pd.DataFrame({"timestamp": ts, "equity": equity})
    curve = build_equity_curve(positions)
    # Return length matches
    assert len(curve) == 5
    # First return zero
    assert curve.loc[curve.index[0], "return"] == 0.0
    # Simple pct change check second point (101/100 -1)
    assert curve.iloc[1]["return"] == pytest.approx(0.01, rel=1e-6)


def test_compute_metrics_basic():
    ts = pd.date_range("2024-01-01", periods=4, freq="1h")
    eq_vals = [100, 101, 100, 102]
    curve = pd.DataFrame({"timestamp": ts, "equity": eq_vals})
    curve = build_equity_curve(curve)
    trades = pd.DataFrame({"dummy": [1, 2]})
    metrics = compute_metrics(trades, curve)
    assert set(metrics.keys()) == {"total_return", "sharpe", "max_drawdown", "trade_count"}
    assert metrics["total_return"] == pytest.approx(0.02, rel=1e-6)  # 102/100 -1
    assert metrics["trade_count"] == 2
    # Determinism
    metrics2 = compute_metrics(trades, curve)
    assert metrics == metrics2


def test_empty_equity_curve():
        metrics = compute_metrics(pd.DataFrame(), pd.DataFrame())
        assert metrics == {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "trade_count": 0}


def _candles(n: int = 120):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += (1 if i % 12 < 6 else -1) * 0.6
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,
                "high": price + 0.3,
                "low": price - 0.3,
                "close": price,
                "volume": 1_000 + i,
            }
        )
    return pd.DataFrame(rows)


def _config():
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 12})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 5, "long_window": 12}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.10}),
        execution=ExecutionSpec(mode="sim", fee_bps=5.0, slippage_bps=5.0),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _pipeline():
    import domain.indicators.sma  # noqa: F401
    cfg = _config()
    candles = _candles(150)
    signals = run_strategy(cfg, candles, candle_hash="dummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, summary = build_state(fills, positions)
    return trades, positions


def test_metrics_computation_expected_schema_and_determinism():
    trades, positions = _pipeline()
    from domain.metrics import calculator
    eq = calculator.build_equity_curve(positions)
    if not eq.empty:
        assert set(["timestamp", "equity", "return"]).issubset(eq.columns)
        # Return series should start with 0
        assert abs(float(eq.iloc[0]["return"])) < 1e-12
    metrics = calculator.compute_metrics(trades, eq)
    for k in ["total_return", "sharpe", "max_drawdown", "trade_count"]:
        assert k in metrics
    assert metrics["trade_count"] == len(trades)
    # Determinism
    trades2, positions2 = _pipeline()
    eq2 = calculator.build_equity_curve(positions2)
    metrics2 = calculator.compute_metrics(trades2, eq2)
    pd.testing.assert_frame_equal(eq, eq2)
    assert metrics == metrics2
