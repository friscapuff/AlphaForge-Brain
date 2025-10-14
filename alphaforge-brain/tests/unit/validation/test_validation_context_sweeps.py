from __future__ import annotations

from domain.schemas.run_config import (
    ExecutionSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)
from models.parameter_definition import ParameterCollection, ParameterMode
from services.validation.context import build_validation_context


def _build_sample_run_config() -> RunConfig:
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(
            name="dual_sma",
            params={
                "fast": {"mode": "list", "values": [5, 8]},
                "slow": {
                    "mode": "range",
                    "range": {"start": 20, "stop": 26, "step": 3},
                },
                "threshold": 0.5,
            },
        ),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="AAPL",
        timeframe="1d",
        start="2024-01-01",
        end="2024-02-01",
        seed=1234,
    )


def test_build_validation_context_attaches_parameter_definitions() -> None:
    api_config = _build_sample_run_config()

    run_config, runtime_config, seed_bundle = build_validation_context(api_config)

    strategy = run_config.strategy
    assert isinstance(strategy.parameter_definitions, ParameterCollection)
    assert strategy.has_sweep is True
    assert strategy.combination_count == 6

    fast_definition = strategy.parameter_definitions.get("fast")
    assert fast_definition is not None
    assert fast_definition.mode is ParameterMode.LIST
    assert fast_definition.unique_values == (5, 8)
    assert strategy.parameters["fast"] == 5

    slow_definition = strategy.parameter_definitions.get("slow")
    assert slow_definition is not None
    assert slow_definition.mode is ParameterMode.RANGE
    assert slow_definition.unique_values == (20, 23, 26)
    assert strategy.parameters["slow"] == 20

    assert strategy.parameter_payload["threshold"]["mode"] == "single"
    assert strategy.raw_parameters["fast"]["values"] == [5, 8]

    # Existing outputs should still be populated
    assert runtime_config.permutation_count > 0
    assert seed_bundle is not None


def test_build_validation_context_handles_non_sweep_payload() -> None:
    api_config = RunConfig(
        indicators=[],
        strategy=StrategySpec(name="momentum", params={"window": 12}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="MSFT",
        timeframe="1d",
        start="2024-03-01",
        end="2024-04-01",
    )

    run_config, _, _ = build_validation_context(api_config)

    strategy = run_config.strategy
    assert strategy.has_sweep is False
    assert strategy.combination_count == 1
    assert strategy.parameters == {"window": 12}
