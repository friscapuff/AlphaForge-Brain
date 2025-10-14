"""Golden-run determinism gate."""

from __future__ import annotations

import copy
from collections.abc import Mapping as MappingABC
from typing import Mapping, cast

from ..baseline import TrustGateBaseline
from ..models import TrustGateResult
from .base import build_result

_DYNAMIC_RUN_KEYS = {"accounting_ledger", "executed_at", "id"}


def _normalise_manifest(manifest: Mapping[str, object]) -> Mapping[str, object]:
    normalised = cast(dict[str, object], copy.deepcopy(manifest))
    run_block = normalised.get("run")
    if isinstance(run_block, dict):
        for key in _DYNAMIC_RUN_KEYS:
            run_block.pop(key, None)
    return normalised


def _mapping_child(
    mapping: Mapping[str, object], key: str
) -> Mapping[str, object] | None:
    value = mapping.get(key)
    if isinstance(value, MappingABC):
        # The manifest snapshot persists dictionaries; convert to a concrete dict for mutation safety.
        return cast(Mapping[str, object], value)
    return None


def evaluate(
    *, candidate_manifest: Mapping[str, object], baseline: TrustGateBaseline
) -> TrustGateResult:
    """Validate that the candidate manifest matches the canonical baseline."""

    gate = baseline.gate("golden_run")

    run_section = _mapping_child(candidate_manifest, "run")
    baseline_run = _mapping_child(baseline.manifest_snapshot, "run")

    raw_config_hash = run_section.get("config_hash") if run_section else None
    config_hash = raw_config_hash if isinstance(raw_config_hash, str) else None

    manifest_match = _normalise_manifest(candidate_manifest) == _normalise_manifest(
        baseline.manifest_snapshot
    )

    candidate_trust_gate = (
        _mapping_child(run_section, "trust_gate") if run_section else None
    )
    baseline_trust_gate = (
        _mapping_child(baseline_run, "trust_gate") if baseline_run else None
    )
    candidate_gates = (
        candidate_trust_gate.get("gates") if candidate_trust_gate else None
    )
    baseline_gates = baseline_trust_gate.get("gates") if baseline_trust_gate else None
    artifact_hash_match = candidate_gates == baseline_gates

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
