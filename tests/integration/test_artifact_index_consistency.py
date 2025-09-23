from __future__ import annotations

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
from lib.artifacts import artifact_index


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
        validation=ValidationSpec(),
        seed=123,
    )


def test_artifact_index_consistency(manifest_loader):  # type: ignore[override]
    app = create_app()  # noqa: F841 (ensure app import side effects, e.g., version injection)
    registry = InMemoryRunRegistry()
    cfg = _schema_run_config()
    run_hash, record, created = create_or_get(cfg, registry, seed=123)
    assert created is True

    manifest = manifest_loader(run_hash)
    idx = artifact_index(run_hash)
    manifest_names = {e.name for e in manifest.entries}
    index_names = {e["name"] for e in idx}
    # Allow index to include 'validation_detail.json' even if not in manifest (writer adds only when present)
    extra_allowed = {"validation_detail.json"}
    assert all((n in manifest_names) or (n in extra_allowed) for n in index_names)
    manifest_hash_map = {e.name: e.sha256 for e in manifest.entries}
    for entry in idx:
        if entry["name"] in manifest_hash_map:  # only assert when manifest has the file
            assert manifest_hash_map.get(entry["name"]) == entry["sha256"], f"Hash mismatch for {entry['name']}"
