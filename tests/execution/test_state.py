from datetime import datetime, timedelta, timezone

import pandas as pd

from domain.execution.simulator import simulate
from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)
from domain.strategy.runner import run_strategy


def _candles(n: int = 60) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += (1 if i % 10 < 5 else -1) * 0.7  # deterministic oscillation
        rows.append({
            "timestamp": base + timedelta(minutes=i),
            "open": price,
            "high": price + 0.4,
            "low": price - 0.4,
            "close": price,
            "volume": 1000 + i,
        })
    return pd.DataFrame(rows)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 4, "slow": 8})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 4, "long_window": 8}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.15}),
        execution=ExecutionSpec(mode="sim", fee_bps=5.0, slippage_bps=10.0),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _pipeline() -> tuple[RunConfig, pd.DataFrame, pd.DataFrame]:
    cfg = _config()
    import domain.indicators.sma  # noqa: F401
    candles = _candles(70)
    signals = run_strategy(cfg, candles, candle_hash="dummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized)
    return cfg, fills, positions


def test_trade_summary_and_cumulative_pnl_deterministic() -> None:
    cfg, fills, positions = _pipeline()
    from domain.execution import state
    trades, summary = state.build_state(fills, positions)
    # May be empty if no complete round trips; allow either but ensure correct schema
    expected_cols = [
        "entry_ts","exit_ts","side","qty","entry_price","exit_price","pnl","return_pct","holding_period"
    ]
    for col in expected_cols:
        if not trades.empty:
            assert col in trades.columns
    # Determinism check: re-run pipeline and compare
    cfg2, fills2, positions2 = _pipeline()
    trades2, summary2 = state.build_state(fills2, positions2)
    pd.testing.assert_frame_equal(trades, trades2)
    assert summary["cumulative_pnl"] == summary2["cumulative_pnl"]
