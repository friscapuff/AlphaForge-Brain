from __future__ import annotations

import json
from pathlib import Path

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

BASELINE_PATH = Path("benchmarks/golden_run_nvda_1d.json")


def _cfg() -> RunConfig:
    return RunConfig(
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-10",
        indicators=[
            IndicatorSpec(name="sma", params={"window": 5}),
            IndicatorSpec(name="sma", params={"window": 15}),
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": 5, "slow": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(permutation={"trials": 5}),
        seed=123,
    )


def test_golden_run_metrics_snapshot() -> None:
    # Skip silently if NVDA dataset missing
    dataset_csv = Path("src/domain/data/NVDA_5y.csv")
    if not dataset_csv.exists():
        return
    reg = InMemoryRunRegistry()
    cfg = _cfg()
    run_hash, rec, _ = create_or_get(cfg, reg, seed=cfg.seed)
    summary = rec.get("summary") or {}
    # Minimal required keys for stability; extend as needed
    keys = [k for k in ["trade_count", "sharpe", "cumulative_return"] if k in summary]
    snap = {k: summary[k] for k in keys}
    snap["run_hash"] = run_hash
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BASELINE_PATH.exists():
        # First creation path: write baseline and pass (intentional bootstrap)
        with BASELINE_PATH.open("w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, sort_keys=True)
        return
    baseline = json.loads(BASELINE_PATH.read_text("utf-8"))
    # Assert stable metrics/hash; if this fails, confirm intentional change then update baseline file explicitly in PR.
    assert (
        baseline == snap
    ), f"Golden run drift detected. Baseline={baseline} Current={snap}"
