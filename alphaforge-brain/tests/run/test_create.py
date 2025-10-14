import json
from pathlib import Path

import pytest
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)


def _config() -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 15})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 5, "long_window": 15}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(mode="sim", fee_bps=2.0, slippage_bps=2.0),
        symbol="CACHE",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-07",
    )


def test_create_or_get_idempotent() -> None:
    from domain.run.create import InMemoryRunRegistry, create_or_get

    cfg = _config()
    registry = InMemoryRunRegistry()
    h1, rec1, created1 = create_or_get(cfg, registry, seed=123)
    h2, rec2, created2 = create_or_get(
        cfg, registry, seed=999
    )  # different seed should not matter once cached
    assert h1 == h2
    assert created1 is True
    assert created2 is False
    # progress events count should be present and not increment on second call
    assert rec1["progress_events"] >= 2  # At least RUNNING + COMPLETE
    assert rec2["progress_events"] == rec1["progress_events"]
    # p-values may be absent if validation disabled; ensure key structure stable
    if "p_values" in rec1 and isinstance(rec1["p_values"], dict):
        assert "perm" in rec1["p_values"]


def _accounting_gate(summary: dict[str, object]) -> dict[str, object]:
    if not isinstance(summary, dict):
        raise AssertionError("trust gate summary malformed")
    entries = summary.get("gates")
    if not isinstance(entries, list):
        entries = summary.get("results")
    if isinstance(entries, list):
        for gate in entries:
            if isinstance(gate, dict) and gate.get("name") == "accounting":
                return gate
    raise AssertionError("accounting gate missing from summary")


def test_accounting_ledger_included_and_persists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _fast_validation_stub,
) -> None:
    from domain.run.create import InMemoryRunRegistry, create_or_get

    from infra.artifacts_root import resolve_artifact_root

    cfg = _config()
    registry = InMemoryRunRegistry()

    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(artifact_root))
    resolve_artifact_root(None)

    run_hash, record, created = create_or_get(cfg, registry, seed=321)
    assert created is True

    ledger = record.get("accounting_ledger")
    assert isinstance(ledger, dict)
    assert ledger.get("run_hash") == run_hash
    assert pytest.approx(ledger.get("equity")) == ledger.get("cash")

    trust_summary = record.get("trust_gate_summary")
    gate = _accounting_gate(trust_summary if isinstance(trust_summary, dict) else {})
    assert gate.get("status") == "pass"
    metrics = gate.get("metrics") if isinstance(gate, dict) else None
    assert isinstance(metrics, dict)
    assert metrics.get("observed_equity") == ledger.get("equity")

    manifest_path = artifact_root / run_hash / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_section = manifest.get("run") if isinstance(manifest, dict) else None
    assert isinstance(run_section, dict)
    persisted_ledger = run_section.get("accounting_ledger")
    assert isinstance(persisted_ledger, dict)
    assert pytest.approx(persisted_ledger.get("equity")) == ledger.get("equity")
