"""Accounting reconciliation gate."""

from __future__ import annotations

from typing import Any, Mapping

from prometheus_client import REGISTRY
from services.audit.governance_logger import (
    emit_governance_metric,
    record_governance_event,
)
from services.trust_gates.accounting import invariants

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def _extract_candidate_ledger(
    manifest: Mapping[str, Any] | None
) -> Mapping[str, Any] | None:
    if not isinstance(manifest, Mapping):
        return None
    run_section = manifest.get("run")
    if not isinstance(run_section, Mapping):
        return None
    ledger = run_section.get("accounting_ledger")
    return ledger if isinstance(ledger, Mapping) else None


def _decimal_to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate(
    *,
    baseline: TrustGateBaseline,
    candidate_manifest: Mapping[str, Any] | None = None,
) -> TrustGateResult:
    gate = baseline.gate("accounting")
    manifest_entry = gate_manifest_entry(baseline, "accounting")
    metrics_block = (
        manifest_entry.get("metrics") if isinstance(manifest_entry, Mapping) else None
    )
    baseline_metrics: Mapping[str, Any] = (
        metrics_block if isinstance(metrics_block, Mapping) else {}
    )

    ledger = _extract_candidate_ledger(candidate_manifest)

    diagnostics: dict[str, Any] = {}
    metrics: dict[str, Any] = {
        "baseline_max_currency_delta": _decimal_to_float(
            baseline_metrics.get("max_currency_delta")
        ),
        "baseline_unmatched_trade_ids": list(
            baseline_metrics.get("unmatched_trade_ids", [])
        ),
    }

    if ledger is None:
        diagnostics["message"] = "Missing accounting ledger payload"
        status = "fail"
        metrics.update(
            {
                "delta": None,
                "tolerance": None,
                "expected_equity": None,
                "observed_equity": None,
            }
        )
        record_governance_event(
            message="accounting_invariants.missing_ledger",
            details={"baseline": metrics["baseline_max_currency_delta"]},
        )
        emit_governance_metric(
            registry=REGISTRY,
            name="accounting_violation",
            description="Accounting ledger missing",
            labels={"event": "accounting_missing_ledger"},
        )
        return build_result(
            gate=gate, status=status, metrics=metrics, diagnostics=diagnostics
        )

    assert ledger is not None  # Narrow for mypy
    result = invariants.evaluate_ledger(ledger)
    metrics.update(
        {
            "delta": _decimal_to_float(result.delta),
            "tolerance": _decimal_to_float(result.tolerance),
            "expected_equity": _decimal_to_float(result.expected_equity),
            "observed_equity": _decimal_to_float(result.observed_equity),
            "trade_ids": list(ledger.get("trade_ids", [])),
        }
    )

    status = "pass" if result.passed else "fail"

    if not result.passed and result.violation is not None:
        diagnostics["message"] = "Accounting invariant breach"
        diagnostics["delta"] = float(result.violation.delta)
        diagnostics["tolerance"] = float(result.violation.tolerance)
        diagnostics["expected_equity"] = float(result.violation.expected_equity)
        diagnostics["observed_equity"] = float(result.violation.observed_equity)
        trade_ids = list(result.violation.trade_ids)
        diagnostics["trade_ids"] = trade_ids
        metrics["trade_ids"] = trade_ids
        record_governance_event(
            message="accounting_invariants.violation",
            details={
                "delta": float(result.violation.delta),
                "tolerance": float(result.violation.tolerance),
                "trade_ids": list(result.violation.trade_ids),
            },
        )
        emit_governance_metric(
            registry=REGISTRY,
            name="accounting_violation",
            description="Accounting invariant failed",
            labels={"event": "accounting_violation"},
        )

    return build_result(
        gate=gate,
        status=status,
        metrics=metrics,
        diagnostics=diagnostics,
    )
