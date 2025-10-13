"""Causality trust gate."""

from __future__ import annotations

from typing import Any, Mapping

from ..baseline import TrustGateBaseline
from ..config_loader import ToleranceProfile
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry

_METRIC_KEYS = ("leakage_score", "equity_drift", "sharpe_ratio")


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_manifest_metrics(manifest: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(manifest, Mapping):
        return {}
    run_section = manifest.get("run")
    if not isinstance(run_section, Mapping):
        return {}
    trust_gate_section = run_section.get("trust_gate")
    if not isinstance(trust_gate_section, Mapping):
        return {}
    gates = trust_gate_section.get("gates")
    if isinstance(gates, list):
        for entry in gates:
            if isinstance(entry, Mapping) and entry.get("name") == "causality":
                metrics = entry.get("metrics")
                return metrics if isinstance(metrics, Mapping) else {}
    return {}


def evaluate(
    *,
    baseline: TrustGateBaseline,
    candidate_manifest: Mapping[str, Any] | None = None,
    tolerance_profile: ToleranceProfile | None = None,
) -> TrustGateResult:
    gate = baseline.gate("causality")
    baseline_entry = gate_manifest_entry(baseline, "causality")
    metrics_block = (
        baseline_entry.get("metrics") if isinstance(baseline_entry, Mapping) else None
    )
    baseline_metrics: Mapping[str, Any] = (
        metrics_block if isinstance(metrics_block, Mapping) else {}
    )

    manifest_metrics = _resolve_manifest_metrics(candidate_manifest)

    resolved_metrics: dict[str, float | None] = {}
    for key in _METRIC_KEYS:
        manifest_value = manifest_metrics.get(key)
        value = _coerce_float(manifest_value)
        if value is None:
            value = _coerce_float(baseline_metrics.get(key))
        resolved_metrics[key] = value

    tolerance_payload: dict[str, object] = {}
    violations: list[dict[str, object]] = []
    if tolerance_profile is not None:
        for name, specification in tolerance_profile.metrics.items():
            tolerance_payload[name] = {
                "threshold": specification.threshold,
                "comparator": specification.comparator,
                "severity": specification.severity,
            }
            actual = resolved_metrics.get(name)
            if actual is None:
                violations.append({"metric": name, "reason": "missing_value"})
                continue
            if not specification.within_bounds(actual):
                violations.append(
                    {
                        "metric": name,
                        "observed": actual,
                        "threshold": specification.threshold,
                        "comparator": specification.comparator,
                    }
                )

    status = "pass" if not violations else "fail"

    diagnostics: dict[str, object] = {}
    if violations:
        diagnostics["message"] = "Causality tolerance breach"
        diagnostics["violations"] = violations

    metrics = {
        "leakage_score": resolved_metrics.get("leakage_score"),
        "equity_drift": resolved_metrics.get("equity_drift"),
        "sharpe_ratio": resolved_metrics.get("sharpe_ratio"),
        "baseline_leakage": _coerce_float(baseline_metrics.get("leakage_score")),
        "baseline_equity_drift": _coerce_float(baseline_metrics.get("equity_drift")),
    }

    return build_result(
        gate=gate,
        status=status,
        metrics=metrics,
        diagnostics=diagnostics,
        tolerance=tolerance_payload,
    )
