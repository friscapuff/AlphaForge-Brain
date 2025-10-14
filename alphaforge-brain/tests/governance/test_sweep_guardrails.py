from __future__ import annotations

import json
from pathlib import Path

import pytest
from domain.run.create import InMemoryRunRegistry
from domain.schemas.run_config import RunConfig
from models.manifest import SweepCapStatus, SweepDataQualityStatus, SweepStatus
from models.parameter_definition import ParameterCollection
from prometheus_client import CollectorRegistry
from services.sweeps.orchestrator import execute_sweep

from infra.config import get_settings


def _build_run_config() -> RunConfig:
    payload: dict[str, object] = {
        "start": "2024-01-01",
        "end": "2024-01-05",
        "symbol": "CAP",
        "timeframe": "1h",
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
    }
    return RunConfig.model_validate(payload)


def test_sweep_guardrail_cap_hit_emits_telemetry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AF_OPTIMIZATION_MAX_COMBINATIONS", "1")
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover - defensive when cache missing
        pass

    base_config = _build_run_config()
    parameters = ParameterCollection.from_raw(
        {
            "fast": {"mode": "list", "values": [5, 8]},
            "slow": {"mode": "list", "values": [30, 45]},
        }
    )
    registry = InMemoryRunRegistry()
    metrics_registry = CollectorRegistry()
    audit_path = tmp_path / "sweep_guardrail.log"

    result = execute_sweep(
        sweep_id="cap-test",
        base_config=base_config,
        parameters=parameters,
        registry=registry,
        metrics_registry=metrics_registry,
        audit_path=audit_path,
    )

    assert result.manifest.status is SweepStatus.FAILED
    assert "OPTIMIZATION_SWEEP_LIMIT_HIT" in result.manifest.notes

    orchestrator_checkpoint = result.manifest.trust_gates.orchestrator
    assert orchestrator_checkpoint is not None
    assert orchestrator_checkpoint.cap_status is SweepCapStatus.HIT
    assert orchestrator_checkpoint.data_quality_status is SweepDataQualityStatus.REVIEW

    assert audit_path.exists()
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    guardrail_entries = [
        entry for entry in records if entry.get("message") == "sweep.guardrail"
    ]
    assert guardrail_entries, "Expected guardrail telemetry entry"
    guardrail_payload = guardrail_entries[-1]
    assert guardrail_payload["cap_status"] == "hit"
    assert guardrail_payload["data_quality_status"] == "review"

    sample = metrics_registry.get_sample_value(
        "sweep_guardrail_events_total",
        {
            "sweep_id": "cap-test",
            "ticker": base_config.symbol,
            "reason": "combination_cap",
            "cap_status": "hit",
            "data_quality_status": "review",
        },
    )
    assert sample is not None
    assert sample >= 1.0

    derived = result.manifest.derived_metrics
    per_ticker = derived["data_quality_status_per_ticker"][base_config.symbol]
    assert per_ticker == "review"
    assert derived["cap_status_per_ticker"][base_config.symbol] == "hit"

    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover
        pass
