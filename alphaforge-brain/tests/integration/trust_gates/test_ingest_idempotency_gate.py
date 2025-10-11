from __future__ import annotations

import importlib

import pytest

from tests.fixtures.trust_gates import load_trust_gate_baseline


@pytest.mark.integration
def test_ingest_idempotency_gate_reports_identical_hashes() -> None:
    """FR-206: Idempotency gate must confirm dataset hashes are stable."""

    gate = importlib.import_module("services.trust_gates.gates.ingest")
    assert hasattr(gate, "evaluate"), "Ingest gate must expose evaluate()"

    baseline = load_trust_gate_baseline()
    result = gate.evaluate(baseline=baseline)

    dataset_hash_match = result.metrics.get("dataset_hash_match")
    assert dataset_hash_match is True
    assert result.status == "pass"
