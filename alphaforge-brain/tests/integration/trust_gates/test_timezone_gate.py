from __future__ import annotations

import importlib

import pytest

from tests.fixtures.trust_gates import load_trust_gate_baseline


@pytest.mark.integration
def test_timezone_gate_flags_no_ambiguous_timestamps() -> None:
    """FR-207: Timezone gate must ensure UTC alignment with no DST ambiguity."""

    gate = importlib.import_module("services.trust_gates.gates.timezone")
    assert hasattr(gate, "evaluate"), "Timezone gate must expose evaluate()"

    baseline = load_trust_gate_baseline()
    result = gate.evaluate(baseline=baseline)

    assert result.metrics.get("ambiguous_timestamps") == 0
    assert result.metrics.get("dst_anomalies") == 0
    assert result.status == "pass"
