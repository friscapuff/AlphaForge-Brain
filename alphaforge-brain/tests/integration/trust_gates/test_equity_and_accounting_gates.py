from __future__ import annotations

import importlib

import pytest

from tests.fixtures.trust_gates import load_trust_gate_baseline


@pytest.mark.integration
def test_equity_and_accounting_gates_balance_ledgers() -> None:
    """FR-204/FR-208: Equity and accounting gates must keep drift within tolerance."""

    equity_gate = importlib.import_module("services.trust_gates.gates.equity")
    accounting_gate = importlib.import_module("services.trust_gates.gates.accounting")

    for gate in (equity_gate, accounting_gate):
        assert hasattr(gate, "evaluate"), f"{gate.__name__} must expose evaluate()"

    baseline = load_trust_gate_baseline()

    equity_result = equity_gate.evaluate(baseline=baseline)
    accounting_result = accounting_gate.evaluate(baseline=baseline)

    assert equity_result.metrics.get("max_basis_point_drift", 1.0) <= 5
    assert accounting_result.metrics.get("max_currency_delta", 0.5) <= 0.05
    assert equity_result.status == "pass"
    assert accounting_result.status == "pass"
