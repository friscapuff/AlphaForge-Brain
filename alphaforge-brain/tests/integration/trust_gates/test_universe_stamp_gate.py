from __future__ import annotations

import importlib

import pytest

from tests.fixtures.trust_gates import load_trust_gate_baseline


@pytest.mark.integration
def test_universe_stamp_gate_detects_missing_symbols() -> None:
    """FR-205: Universe stamp gate must detect no missing symbols in canonical baseline."""

    gate = importlib.import_module("services.trust_gates.gates.universe")
    assert hasattr(gate, "evaluate"), "Universe gate must expose evaluate()"

    baseline = load_trust_gate_baseline()
    result = gate.evaluate(baseline=baseline)

    missing = result.metrics.get("missing_symbols")
    assert isinstance(missing, list)
    assert not missing
    assert result.status == "pass"
