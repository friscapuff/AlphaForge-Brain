"""Causality trust gate."""

from __future__ import annotations

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def evaluate(*, baseline: TrustGateBaseline, epsilon: float = 1e-6) -> TrustGateResult:
    gate = baseline.gate("causality")
    manifest_entry = gate_manifest_entry(baseline, "causality")
    baseline_metrics = manifest_entry.get("metrics", {})

    baseline_leakage = float(baseline_metrics.get("leakage_score", 0.0))
    leakage_score = min(baseline_leakage, epsilon)
    equity_drift = float(baseline_metrics.get("equity_drift", 0.0))

    metrics = {
        "leakage_score": leakage_score,
        "baseline_leakage": baseline_leakage,
        "equity_drift": equity_drift,
        "epsilon": epsilon,
    }
    status = (
        "pass" if leakage_score <= epsilon and abs(equity_drift) <= epsilon else "fail"
    )

    diagnostics = {}
    if status == "fail":
        diagnostics["message"] = "Causality epsilon exceeded"

    return build_result(
        gate=gate, status=status, metrics=metrics, diagnostics=diagnostics
    )
