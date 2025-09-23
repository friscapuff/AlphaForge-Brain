"""Test env-driven artifact root override (AlphaForgeB Brain).

Ensures ALPHAFORGEB_ARTIFACT_ROOT directs outputs away from default ./artifacts.
"""

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
)


def test_artifact_root_env_override(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "af_outputs"
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(target))
    cfg = RunConfig(
        symbol="TEST", timeframe="1m", start="2024-01-01", end="2024-01-02",
        indicators=[IndicatorSpec(name="sma", params={"window":5}), IndicatorSpec(name="sma", params={"window":10})],
        strategy=StrategySpec(name="dual_sma", params={"fast":5, "slow":10}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction":0.1}),
        execution=ExecutionSpec(slippage_bps=0, fee_bps=0)
    )
    reg = InMemoryRunRegistry()
    run_hash, rec, created = create_or_get(cfg, reg, seed=42)
    assert created is True
    run_dir = target / run_hash
    assert run_dir.exists(), "Artifacts not written to env override root"
    manifest_path = run_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text("utf-8"))
    assert manifest.get("run_hash") == run_hash
    # Ensure default directory absent (idempotent) unless reused by other tests
    default_dir = Path("artifacts") / run_hash
    assert not default_dir.exists(), "Run artifacts unexpectedly written to default root when env override active"

__all__ = ["test_artifact_root_env_override"]
