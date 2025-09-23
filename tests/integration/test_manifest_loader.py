from __future__ import annotations

import pytest

from api.app import create_app
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def _schema_run_config() -> RunConfig:
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        indicators=[IndicatorSpec(name="sma", params={"window":5}), IndicatorSpec(name="sma", params={"window":15})],
        strategy=StrategySpec(name="dual_sma", params={"fast":5, "slow":15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction":0.1}),
        execution=ExecutionSpec(slippage_bps=0.0),
        validation=ValidationSpec(
            permutation={"samples": 4},
            block_bootstrap={"samples": 4, "blocks": 2},
            monte_carlo={"paths": 4},
            walk_forward={"folds": 2},
        ),
        seed=42,
    )

@pytest.mark.integration
def test_manifest_loader_integrity(manifest_loader):  # type: ignore[override]
    _app = create_app()
    registry = InMemoryRunRegistry()
    cfg = _schema_run_config()
    run_hash, record, created = create_or_get(cfg, registry, seed=42)
    assert created is True
    # Ensure manifest file exists
    manifest = manifest_loader(run_hash)
    # Artifacts listed in manifest should have non-empty hash strings
    for e in manifest.entries:
        assert e.sha256 and len(e.sha256) == 64
    # Re-run identical config -> reuse existing (idempotent)
    run_hash2, record2, created2 = create_or_get(cfg, registry, seed=42)
    assert run_hash2 == run_hash
    assert created2 is False
    # Composite hash stable across re-loads
    manifest2 = manifest_loader(run_hash2)
    assert manifest2.canonical_hash() == manifest.canonical_hash()
