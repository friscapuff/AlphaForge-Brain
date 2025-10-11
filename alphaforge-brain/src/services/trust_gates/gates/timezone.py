"""Timezone normalization gate."""

from __future__ import annotations

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def evaluate(*, baseline: TrustGateBaseline) -> TrustGateResult:
    gate = baseline.gate("timezone")
    manifest_entry = gate_manifest_entry(baseline, "timezone")
    baseline_metrics = manifest_entry.get("metrics", {})

    metrics = {
        "ambiguous_timestamps": int(baseline_metrics.get("ambiguous_timestamps", 0)),
        "dst_anomalies": int(baseline_metrics.get("dst_anomalies", 0)),
        "leap_seconds_detected": int(baseline_metrics.get("leap_seconds_detected", 0)),
    }

    status = (
        "pass"
        if metrics["ambiguous_timestamps"] == 0 and metrics["dst_anomalies"] == 0
        else "fail"
    )

    return build_result(gate=gate, status=status, metrics=metrics)
