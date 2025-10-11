"""Shared helpers for trust gate evaluators."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from ..baseline import GateBaseline, TrustGateBaseline
from ..models import TrustGateResult


def build_result(
    *,
    gate: GateBaseline,
    status: str,
    metrics: Mapping[str, object],
    diagnostics: Optional[Mapping[str, object]] = None,
) -> TrustGateResult:
    """Create a :class:`TrustGateResult` populated with baseline metadata."""

    return TrustGateResult(
        name=gate.name,
        status=status,
        metrics=dict(metrics),
        diagnostics=dict(diagnostics or {}),
        artifact=gate.artifact,
        correlation_id=gate.correlation_id,
    )


def gate_manifest_entry(
    baseline: TrustGateBaseline | Any, gate_name: str
) -> Mapping[str, object]:
    """Return the manifest snapshot entry for the requested gate.

    Supports both the production :class:`TrustGateBaseline` and the
    ``TrustGateBaselineFixture`` provided in the test suite.
    """

    manifest = getattr(baseline, "manifest_snapshot", None)
    if not isinstance(manifest, Mapping):
        raise ValueError("Baseline object does not expose manifest_snapshot mapping")

    run_section = manifest.get("run", {})
    trust_gate_section = run_section.get("trust_gate", {})
    gates = trust_gate_section.get("gates", [])

    for entry in gates:
        if entry.get("name") == gate_name:
            return entry

    raise KeyError(f"Gate '{gate_name}' not present in manifest snapshot")
