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


def _candles(days: int = 90) -> pd.DataFrame:
    # 1-minute bars for ~90 days (~129600 minutes) but we can downscale for test brevity
    # We'll simulate 6 hours per day to keep size modest: 6*60=360 per day
    rows = []
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    for d in range(days):
        for m in range(360):
            i = d * 360 + m
            # cyclic drift pattern
            price += (1 if (i // 50) % 2 == 0 else -1) * 0.15
            ts = base + timedelta(minutes=i)
            rows.append(
                {
                    "timestamp": ts,
                    "open": price,
                    "high": price + 0.1,
                    "low": price - 0.1,
                    "close": price,
                    "volume": 1000 + i,
                }
            )
    return pd.DataFrame(rows)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 8, "slow": 21})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 8, "long_window": 21}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.12}),
        execution=ExecutionSpec(mode="sim", fee_bps=2.0, slippage_bps=2.0),
        symbol="WF",
        timeframe="1m",
        start="2024-01-01",
        end="2024-07-01",
    )


def _pipeline() -> tuple[pd.DataFrame, pd.DataFrame]:
    import domain.indicators.sma  # noqa: F401

    cfg = _config()
    candles = _candles(30)  # 30 days * 360 = 10800 bars
    signals = run_strategy(cfg, candles, candle_hash="dummywf")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, positions_df = build_state(fills, positions)
    return trades, positions_df


def test_walk_forward_report_basic() -> None:
    trades, positions_df = _pipeline()
    from domain.validation import walk_forward_report

    report = walk_forward_report(trades, positions_df, n_folds=5)
    assert len(report) == 5 or len(report) == len(
        trades
    )  # fallback if trades fewer than folds
    # Required keys present per fold
    required = {"fold", "start", "end", "n_trades", "sharpe", "return", "max_dd"}
    for i, fold in enumerate(report, start=1):
        assert required.issubset(fold.keys())
        assert fold["fold"] == i
        # Non-negative trade count
        assert fold["n_trades"] > 0
    # Temporal ordering
    starts = [f["start"] for f in report]
    assert starts == sorted(starts)
