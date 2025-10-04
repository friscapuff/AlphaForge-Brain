import json
from pathlib import Path
from typing import Any

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def make_config() -> RunConfig:
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        initial_equity=10000.0,
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
        strategy=StrategySpec(name="dual_sma", params={}),
        risk=RiskSpec(
            name="fixed_fraction", model="fixed_fraction", params={"fraction": 0.1}
        ),
        execution=ExecutionSpec(slippage_bps=1, fee_perc=0.0005),
        validation=ValidationSpec(
            permutation={"samples": 10},
            block_bootstrap={"blocks": 5, "samples": 8},
            monte_carlo={"paths": 7},
            walk_forward={"folds": 3},
        ),
        seed=123,
    )


def test_validation_merge_artifact(tmp_path: Path, monkeypatch: Any) -> None:
    registry = InMemoryRunRegistry()
    cfg = make_config()
    run_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
    assert created is True

    # After implementation we expect writer to have produced artifacts/<hash>/validation_detail.json
    # For now this should fail (file missing) until T038 implemented.
    detail_path = Path("artifacts") / run_hash / "validation_detail.json"
    if detail_path.exists():
        data = json.loads(detail_path.read_text("utf-8"))
        # Expected keys (will be asserted after implementation)
        expected_sections = {
            "permutation",
            "block_bootstrap",
            "monte_carlo_slippage",
            "walk_forward",
        }
        assert expected_sections.issubset(data.keys())
    else:
        raise AssertionError(
            "validation_detail.json not produced yet (expected failure before T038 implementation)"
        )
