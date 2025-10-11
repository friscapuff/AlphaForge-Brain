"""Accounting reconciliation gate."""

from __future__ import annotations

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def evaluate(*, baseline: TrustGateBaseline) -> TrustGateResult:
    gate = baseline.gate("accounting")
    manifest_entry = gate_manifest_entry(baseline, "accounting")
    baseline_metrics = manifest_entry.get("metrics", {})

    max_currency_delta = float(baseline_metrics.get("max_currency_delta", 0.0))
    unmatched_trade_ids = list(baseline_metrics.get("unmatched_trade_ids", []))

    metrics = {
        "max_currency_delta": max_currency_delta,
        "unmatched_trade_ids": unmatched_trade_ids,
    }

    status = (
        "pass" if max_currency_delta <= 0.05 and not unmatched_trade_ids else "fail"
    )

    return build_result(gate=gate, status=status, metrics=metrics)
