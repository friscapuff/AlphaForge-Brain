from __future__ import annotations

import importlib

import pytest

from tests.fixtures.trust_gates import load_trust_gate_baseline


@pytest.mark.integration
def test_causality_gate_collapses_leakage_to_zero() -> None:
    """FR-203: Causality gate must report near-zero leakage on baseline dataset."""

    gate = importlib.import_module("services.trust_gates.gates.causality")
    assert hasattr(gate, "evaluate"), "Causality gate must expose evaluate()"

    baseline = load_trust_gate_baseline()
    result = gate.evaluate(baseline=baseline, epsilon=1e-6)

    leakage_score = result.metrics.get("leakage_score")
    assert leakage_score is not None, "Leakage score metric missing"
    assert leakage_score <= 1e-6
    assert result.status == "pass"
