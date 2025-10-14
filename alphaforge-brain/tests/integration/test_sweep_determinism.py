from __future__ import annotations

from typing import Any

from domain.run.orchestrator import build_sweep_execution_plan
from domain.schemas.run_config import RunConfig
from models.parameter_definition import ParameterCollection

from infra.utils.hash import hash_canonical


def _base_config() -> RunConfig:
    payload: dict[str, Any] = {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "symbol": "DET",
        "timeframe": "1m",
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "validation": {"permutation": {"trials": 8}},
    }
    return RunConfig.model_validate(payload)


def test_sweep_execution_plan_is_deterministic() -> None:
    config = _base_config()
    parameters = ParameterCollection.from_raw(
        {
            "fast": {"mode": "list", "values": [5, 8]},
            "slow": {"mode": "range", "range": {"start": 30, "stop": 61, "step": 15}},
        }
    )

    plan_first = build_sweep_execution_plan(config, parameters)
    plan_second = build_sweep_execution_plan(config, parameters)

    expected_combinations = [
        {"fast": 5, "slow": 30},
        {"fast": 5, "slow": 45},
        {"fast": 5, "slow": 60},
        {"fast": 8, "slow": 30},
        {"fast": 8, "slow": 45},
        {"fast": 8, "slow": 60},
    ]

    assert [entry.parameters for entry in plan_first] == expected_combinations
    assert [entry.parameters for entry in plan_second] == expected_combinations

    combination_ids_first = [entry.combination_id for entry in plan_first]
    combination_ids_second = [entry.combination_id for entry in plan_second]

    assert combination_ids_first == combination_ids_second
    assert len(set(combination_ids_first)) == len(expected_combinations)

    expected_ids = [
        hash_canonical(
            {
                "symbol": config.symbol,
                "timeframe": config.timeframe,
                "strategy": config.strategy.name,
                "parameters": combo,
            }
        )
        for combo in expected_combinations
    ]
    assert combination_ids_first == expected_ids

    run_configs = [entry.run_config for entry in plan_first]
    run_hashes = [rc.canonical_hash() for rc in run_configs]
    assert len(set(run_hashes)) == len(expected_combinations)
    assert all(
        rc.strategy.params == combo
        for rc, combo in zip(run_configs, expected_combinations)
    )

    # Ensure original config remains untouched
    assert config.strategy.params == {"fast": 5, "slow": 20}
