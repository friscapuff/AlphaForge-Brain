from __future__ import annotations

import json
from pathlib import Path

import pytest
from domain.run.create import InMemoryRunRegistry
from domain.schemas.run_config import RunConfig
from models.parameter_definition import ParameterCollection
from prometheus_client import CollectorRegistry
from services.sweeps.orchestrator import execute_sweep


def _build_run_config() -> RunConfig:
    payload: dict[str, object] = {
        "start": "2024-01-01",
        "end": "2024-01-05",
        "symbol": "TEST",
        "timeframe": "1h",
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
    }
    return RunConfig.model_validate(payload)


def test_sweep_telemetry_records_checkpoint_payload(tmp_path: Path) -> None:
    base_config = _build_run_config()
    parameters = ParameterCollection.from_raw(
        {
            "fast": {"mode": "list", "values": [5, 8]},
            "slow": {"mode": "single", "value": 30},
        }
    )
    registry = InMemoryRunRegistry()
    metrics_registry = CollectorRegistry()
    audit_path = tmp_path / "sweep_audit.log"

    result = execute_sweep(
        sweep_id="telemetry-test",
        base_config=base_config,
        parameters=parameters,
        registry=registry,
        metrics_registry=metrics_registry,
        audit_path=audit_path,
    )

    assert audit_path.exists()
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records, "Telemetry audit log must contain entries"
    orchestrator_entries = [
        entry
        for entry in records
        if entry.get("message") == "sweep.checkpoint"
        and entry.get("checkpoint") == "orchestrator"
    ]
    assert orchestrator_entries, "Expected orchestrator checkpoint emission"
    payload = orchestrator_entries[-1]
    assert payload["cap_status"] == "ok"
    assert payload["data_quality_status"] == "pass"

    sample = metrics_registry.get_sample_value(
        "sweep_checkpoint_latency_seconds_count",
        {
            "sweep_id": "telemetry-test",
            "ticker": base_config.symbol,
            "checkpoint": "orchestrator",
            "cap_status": "ok",
            "data_quality_status": "pass",
        },
    )
    assert sample is not None
    assert sample >= 1.0
    manifest = result.manifest
    assert manifest.trust_gates.orchestrator is not None
    assert manifest.trust_gates.orchestrator.data_quality_status.value == "pass"
    assert manifest.derived_metrics["latency_ms_per_ticker"][base_config.symbol] >= 0
    assert manifest.derived_metrics["overall_data_quality_status"] == "pass"

    # Ensure combinations metric increments by executed combos (two values -> 2 combos)
    combos = metrics_registry.get_sample_value(
        "sweep_combinations_total",
        {
            "sweep_id": "telemetry-test",
            "ticker": base_config.symbol,
            "checkpoint": "orchestrator",
            "cap_status": "ok",
            "data_quality_status": "pass",
        },
    )
    assert combos is not None
    expected_executed = sum(
        1 for combo in result.manifest.combinations if combo.status.value == "succeeded"
    )
    assert combos == pytest.approx(float(expected_executed))
