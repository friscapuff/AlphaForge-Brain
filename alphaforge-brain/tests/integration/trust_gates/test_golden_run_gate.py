from __future__ import annotations

import importlib

import pytest

from tests.fixtures.trust_gates import load_trust_gate_baseline


@pytest.mark.integration
def test_golden_run_gate_passes_on_canonical_baseline() -> None:
    """FR-202: Golden run gate must recognize canonical baseline as passing."""

    gate = importlib.import_module("services.trust_gates.gates.golden_run")
    assert hasattr(gate, "evaluate"), "Golden run gate must expose evaluate()"

    baseline = load_trust_gate_baseline()
    result = gate.evaluate(
        candidate_manifest=baseline.manifest_snapshot, baseline=baseline
    )

    assert result.status == "pass"
    assert result.metrics["config_hash_match"] is True
    assert not result.diagnostics.get(
        "differences"
    ), "Unexpected manifest differences reported"
