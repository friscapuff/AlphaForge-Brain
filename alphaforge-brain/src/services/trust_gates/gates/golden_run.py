"""Golden-run determinism gate."""

from __future__ import annotations

from typing import Mapping

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result


def evaluate(
    *, candidate_manifest: Mapping[str, object], baseline: TrustGateBaseline
) -> TrustGateResult:
    """Validate that the candidate manifest matches the canonical baseline."""

    gate = baseline.gate("golden_run")

    config_hash = candidate_manifest.get("run", {}).get("config_hash")
    manifest_match = candidate_manifest == baseline.manifest_snapshot
    artifact_hash_match = candidate_manifest.get("run", {}).get("trust_gate", {}).get(
        "gates"
    ) == baseline.manifest_snapshot.get("run", {}).get("trust_gate", {}).get("gates")

    diagnostics = {}
    if not manifest_match:
        diagnostics["differences"] = ["manifest_snapshot"]

    metrics = {
        "config_hash_match": bool(config_hash and config_hash == baseline.config_hash),
        "manifest_match": manifest_match,
        "artifact_listing_match": artifact_hash_match,
    }

    status = "pass" if all(metrics.values()) else "fail"

    return build_result(
        gate=gate, status=status, metrics=metrics, diagnostics=diagnostics
    )
