"""Tests for causality tolerance enforcement (US1/T005)."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from services.trust_gates.config_loader import ToleranceConfigError
from services.trust_gates.suite_service import TrustGateSuiteService

from tests.fixtures.trust_gates import load_manifest_snapshot


def _build_candidate_manifest(**metric_overrides: float) -> dict[str, Any]:
    """Return a candidate manifest with optional causality metric overrides."""

    manifest: dict[str, Any] = copy.deepcopy(load_manifest_snapshot())
    trust_gate = manifest.setdefault("run", {}).setdefault("trust_gate", {})
    gates = trust_gate.setdefault("gates", [])
    for gate in gates:
        if gate.get("name") == "causality":
            metrics = gate.setdefault("metrics", {})
            metrics.update(metric_overrides)
            break
    else:  # pragma: no cover - defensive append for clarity if baseline ever changes
        gates.append(
            {
                "name": "causality",
                "status": "pass",
                "metrics": dict(metric_overrides),
            }
        )
    return manifest


def _extract_gate(summary, name: str):
    for result in summary.results:
        if result.name == name:
            return result
    raise AssertionError(f"Gate {name!r} not present in summary")


def test_causality_gate_fails_when_thresholds_breached() -> None:
    service = TrustGateSuiteService(tolerance_profile="causality")
    manifest = _build_candidate_manifest(
        leakage_score=0.12,
        equity_drift=0.02,
        sharpe_ratio=-0.4,
    )

    summary = service.run(candidate_manifest=manifest, config_hash="test-config-breach")

    assert summary.status == "fail"
    causality = _extract_gate(summary, "causality")
    assert causality.status == "fail"
    assert pytest.approx(0.12, rel=1e-6) == causality.metrics.get("leakage_score")
    assert pytest.approx(0.02, rel=1e-6) == causality.metrics.get("equity_drift")
    assert pytest.approx(-0.4, rel=1e-6) == causality.metrics.get("sharpe_ratio")
    assert causality.diagnostics, "Expected diagnostics describing the tolerance breach"


def test_manifest_block_includes_tolerance_metadata() -> None:
    service = TrustGateSuiteService(tolerance_profile="causality")
    manifest = _build_candidate_manifest(
        leakage_score=0.01,
        equity_drift=0.0001,
        sharpe_ratio=1.8,
    )

    summary = service.run(candidate_manifest=manifest, config_hash="test-config-pass")

    block = summary.manifest_block()
    assert block["tolerance_profile"] == service.tolerance_profile
    assert block.get(
        "tolerance_profile_version"
    ), "SLA version must be surfaced in manifest block"
    assert block.get(
        "tolerance_profile_hash"
    ), "SLA hash must be surfaced in manifest block"
    assert block["config_hash"] == summary.config_hash


def test_missing_tolerance_profile_fails_closed() -> None:
    service = TrustGateSuiteService(tolerance_profile="missing-profile")
    manifest = _build_candidate_manifest()

    with pytest.raises(ToleranceConfigError, match="tolerance profile"):
        service.run(candidate_manifest=manifest)
