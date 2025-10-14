from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

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


def test_telemetry_recorded_within_sixty_seconds(tmp_path: Path) -> None:
    base_config = _build_run_config()
    parameters = ParameterCollection.from_raw(
        {
            "fast": {"mode": "list", "values": [5, 8]},
            "slow": {"mode": "single", "value": 30},
        }
    )
    registry = InMemoryRunRegistry()
    metrics_registry = CollectorRegistry()
    audit_path = tmp_path / "telemetry_latency.log"

    execute_sweep(
        sweep_id="latency-check",
        base_config=base_config,
        parameters=parameters,
        registry=registry,
        metrics_registry=metrics_registry,
        audit_path=audit_path,
    )

    assert audit_path.exists()
    lines = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines, "Expected telemetry audit records"
    now = datetime.now(timezone.utc)
    for entry in lines:
        recorded = entry.get("recorded_at")
        if not recorded:
            continue
        timestamp = datetime.fromisoformat(recorded)
        delta = abs((now - timestamp).total_seconds())
        assert (
            delta <= 60
        ), f"Telemetry latency budget violated: delta={delta:.3f}s for {entry.get('message')}"
