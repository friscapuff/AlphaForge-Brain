"""Equity reconciliation gate."""

from __future__ import annotations

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def evaluate(*, baseline: TrustGateBaseline) -> TrustGateResult:
    gate = baseline.gate("equity_reconciliation")
    manifest_entry = gate_manifest_entry(baseline, "equity_reconciliation")
    baseline_metrics = manifest_entry.get("metrics", {})

    max_basis_point_drift = float(baseline_metrics.get("max_basis_point_drift", 0.0))
    max_currency_delta = float(baseline_metrics.get("max_currency_delta", 0.0))

    metrics = {
        "max_basis_point_drift": max_basis_point_drift,
        "max_currency_delta": max_currency_delta,
    }

    status = (
        "pass" if max_basis_point_drift <= 5 and max_currency_delta <= 0.05 else "fail"
    )

    return build_result(gate=gate, status=status, metrics=metrics)
