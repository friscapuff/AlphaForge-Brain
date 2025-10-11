"""Universe stamp gate."""

from __future__ import annotations

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def evaluate(*, baseline: TrustGateBaseline) -> TrustGateResult:
    gate = baseline.gate("universe_stamp")
    manifest_entry = gate_manifest_entry(baseline, "universe_stamp")
    baseline_metrics = manifest_entry.get("metrics", {})

    missing_symbols = list(baseline_metrics.get("missing_symbols", []))
    status = "pass" if not missing_symbols else "fail"

    metrics = {
        "missing_symbols": missing_symbols,
    }

    return build_result(gate=gate, status=status, metrics=metrics)
