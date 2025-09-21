from __future__ import annotations

import pytest

from domain.run.orchestrator import orchestrate
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)


def _base_config() -> RunConfig:
    return RunConfig(
        symbol="UNREG",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-10",
        indicators=[
            IndicatorSpec(name="sma", params={"window": 3}),
            IndicatorSpec(name="sma", params={"window": 5}),
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": 3, "slow": 5}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(),
    )


def test_missing_symbol_timeframe_error() -> None:
    cfg = _base_config()
    with pytest.raises(RuntimeError):
        orchestrate(cfg)