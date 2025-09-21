
import pytest

# These imports will fail until T009 implemented
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def test_indicator_spec_basic() -> None:
    spec = IndicatorSpec(name="sma", params={"window": 20})
    assert spec.name == "sma"
    assert spec.params["window"] == 20


def test_strategy_spec_basic() -> None:
    spec = StrategySpec(name="dual_sma", params={"fast": 10, "slow": 30})
    assert spec.params["fast"] < spec.params["slow"]


def test_risk_spec_defaults() -> None:
    spec = RiskSpec(model="fixed_fraction", params={"fraction": 0.1})
    assert 0 < spec.params["fraction"] <= 1


def test_execution_spec_defaults() -> None:
    spec = ExecutionSpec(mode="sim", slippage_bps=1.5, fee_bps=0.5)
    assert spec.mode == "sim"
    assert spec.slippage_bps >= 0


def test_validation_spec_empty_defaults() -> None:
    spec = ValidationSpec()
    assert spec.permutation is None
    assert spec.block_bootstrap is None
    assert spec.monte_carlo is None
    assert spec.walk_forward is None


def test_run_config_hash_stability() -> None:
    cfg1 = RunConfig(
        indicators=[IndicatorSpec(name="sma", params={"window": 20})],
        strategy=StrategySpec(name="dual_sma", params={"fast": 10, "slow": 30}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(mode="sim", slippage_bps=1.5, fee_bps=0.5),
        validation=ValidationSpec(),
        symbol="AAPL",
        timeframe="1d",
        start="2024-01-01",
        end="2024-06-01",
        seed=42,
    )
    cfg2 = RunConfig(**cfg1.model_dump())
    assert cfg1.canonical_hash() == cfg2.canonical_hash()


def test_run_config_validation_fast_slower_than_slow() -> None:
    with pytest.raises(ValueError):
        RunConfig(
            indicators=[IndicatorSpec(name="sma", params={"window": 5})],
            strategy=StrategySpec(name="dual_sma", params={"fast": 50, "slow": 10}),
            risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
            execution=ExecutionSpec(mode="sim", slippage_bps=1.5, fee_bps=0.5),
            validation=ValidationSpec(),
            symbol="AAPL",
            timeframe="1d",
            start="2024-01-01",
            end="2024-06-01",
            seed=7,
        )
