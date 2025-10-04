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


def _candles(n: int = 240) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, Any]] = []
    price = 120.0
    for i in range(n):
        price += (1 if i % 40 < 20 else -1) * 0.3
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,
                "high": price + 0.15,
                "low": price - 0.15,
                "close": price,
                "volume": 800 + i,
            }
        )
    return pd.DataFrame(rows)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 6, "slow": 24})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 6, "long_window": 24}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(mode="sim", fee_bps=3.0, slippage_bps=3.0),
        symbol="ORCH",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _manual_pipeline(cfg: RunConfig) -> pd.DataFrame:
    import domain.indicators.sma  # noqa: F401

    candles = _candles(360)
    signals = run_strategy(cfg, candles, candle_hash="orchdummy")
    sized = apply_risk(cfg, signals)
    fills, positions = simulate(cfg, sized, flatten_end=True)
    trades, _summary = build_state(fills, positions)
    return trades


def test_orchestrator_run_state_sequence() -> None:
    from domain.run import Orchestrator, OrchestratorState

    cfg = _config()
    seq: list[Any] = []
    orch = Orchestrator(cfg, seed=123)
    orch.on_progress(lambda st, payload: seq.append(st))
    result = orch.run()
    assert orch.state == OrchestratorState.COMPLETE
    # Ensure expected ordered states visited (allow payload states list may contain duplicates if extended later)
    assert seq[0] == OrchestratorState.RUNNING
    assert OrchestratorState.VALIDATING in seq
    assert seq[-1] == OrchestratorState.COMPLETE
    # Result structure
    assert "trades" in result and "validation" in result
    # permutation_p may be None if permutation validation disabled; assert key presence
    assert "permutation_p" in result["validation"]["summary"]


def test_orchestrator_idempotent_second_run() -> None:
    from domain.run import Orchestrator

    cfg = _config()
    orch = Orchestrator(cfg, seed=42)
    r1 = orch.run()
    r2 = orch.run()
    # Should not rebuild pipeline on second run (same object identity for nested frames is acceptable to assert by equality of summary keys)
    assert r1["summary"] == r2["summary"]


def test_orchestrator_cancel_before_run() -> None:
    from domain.run import Orchestrator, OrchestratorState

    cfg = _config()
    orch = Orchestrator(cfg, seed=77)
    orch.cancel()
    result = orch.run()
    assert orch.state == OrchestratorState.CANCELLED
    assert result.get("cancelled") is True
