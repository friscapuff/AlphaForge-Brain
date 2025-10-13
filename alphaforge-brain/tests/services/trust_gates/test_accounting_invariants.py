"""Accounting invariant regression tests (US2/T018)."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

from prometheus_client import CollectorRegistry
from services.trust_gates.accounting import invariants
from services.trust_gates.suite_service import TrustGateSuiteService

from tests.fixtures.governance_factories import build_accounting_ledger


def _ledger(**overrides: Any) -> dict[str, Any]:
    return build_accounting_ledger(**overrides)


def test_accounting_invariants_pass_for_balanced_ledger() -> None:
    ledger = _ledger()

    result = invariants.evaluate_ledger(ledger)

    assert result.passed is True
    assert result.delta == Decimal("0")
    assert result.violation is None


def test_accounting_invariants_detect_violation() -> None:
    ledger = _ledger(equity=1_030_000.0)

    result = invariants.evaluate_ledger(ledger)

    assert result.passed is False
    assert result.violation is not None
    assert result.violation.trade_ids == tuple(ledger["trade_ids"])
    assert result.delta != Decimal("0")


def _inject_ledger(manifest: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    manifest_copy = copy.deepcopy(manifest)
    run_section = manifest_copy.setdefault("run", {})
    run_section["accounting_ledger"] = ledger
    return manifest_copy


def _get_gate(summary, name: str):
    for gate in summary.results:
        if gate.name == name:
            return gate
    raise AssertionError(f"Gate {name!r} missing from summary")


def test_accounting_gate_surfaces_violation() -> None:
    service = TrustGateSuiteService()
    ledger = _ledger(equity=ledger_expected_equity() + 12.5, tolerance=0.1)
    manifest = _inject_ledger(service.baseline.manifest_snapshot, ledger)
    registry = CollectorRegistry()

    summary = service.run(
        only=("accounting",),
        candidate_manifest=manifest,
        registry=registry,
        config_hash="test-accounting-breach",
    )

    assert summary.status == "fail"
    gate = _get_gate(summary, "accounting")
    assert gate.status == "fail"
    assert gate.metrics.get("delta")
    assert gate.diagnostics


def ledger_expected_equity() -> float:
    ledger = _ledger()
    cash = ledger["cash"]
    unrealized = ledger["unrealized_pnl"]
    fees = ledger["fees"]
    return float(cash + unrealized + fees)
