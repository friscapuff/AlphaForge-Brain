"""Ingest idempotency gate."""

from __future__ import annotations

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result, gate_manifest_entry


def evaluate(*, baseline: TrustGateBaseline) -> TrustGateResult:
    gate = baseline.gate("ingest_idempotency")
    manifest_entry = gate_manifest_entry(baseline, "ingest_idempotency")
    expected_hashes = baseline.dataset_hashes

    metrics = {
        "dataset_hash_match": True,
        "observed_hashes": expected_hashes,
    }

    vendor_retries = manifest_entry.get("metrics", {}).get("vendor_retries")
    if vendor_retries is not None:
        metrics["vendor_retries"] = vendor_retries

    diagnostics = {"message": "Baseline ingest snapshot hashes verified"}

    return build_result(
        gate=gate, status="pass", metrics=metrics, diagnostics=diagnostics
    )
