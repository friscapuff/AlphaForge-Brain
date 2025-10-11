from __future__ import annotations

import importlib

import pytest
from structlog.testing import capture_logs


@pytest.mark.integration
def test_trust_gate_metrics_emit_structlog_and_prometheus() -> None:
    """FR-211: Telemetry module must emit structlog events and Prometheus samples."""

    telemetry = importlib.import_module("services.trust_gates.telemetry")
    assert hasattr(
        telemetry, "create_registry"
    ), "Telemetry must provide create_registry()"
    assert hasattr(
        telemetry, "emit_gate_metrics"
    ), "Telemetry must provide emit_gate_metrics()"

    registry = telemetry.create_registry()

    with capture_logs() as logs:
        telemetry.emit_gate_metrics(
            registry=registry,
            gate="golden_run",
            status="pass",
            duration_ms=1234,
        )

    assert any(entry.get("event") == "trust_gate.result" for entry in logs)

    sample = registry.get_sample_value(
        "trust_gate_status",
        labels={"gate": "golden_run", "status": "pass"},
    )
    assert sample == 1.0
