"""Telemetry safeguards for trust gate execution (US1/T005A)."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from prometheus_client import CollectorRegistry
from services.trust_gates import telemetry
from services.trust_gates.config_loader import ToleranceConfigError
from services.trust_gates.suite_service import TrustGateSuiteService

from tests.fixtures.trust_gates import load_manifest_snapshot


def _build_candidate_manifest(**metric_overrides: float) -> dict[str, Any]:
    manifest: dict[str, Any] = copy.deepcopy(load_manifest_snapshot())
    trust_gate = manifest.setdefault("run", {}).setdefault("trust_gate", {})
    gates = trust_gate.setdefault("gates", [])
    for gate in gates:
        if gate.get("name") == "causality":
            metrics = gate.setdefault("metrics", {})
            metrics.update(metric_overrides)
            break
    else:
        gates.append(
            {"name": "causality", "status": "pass", "metrics": dict(metric_overrides)}
        )
    return manifest


@pytest.fixture()
def registry() -> CollectorRegistry:
    return telemetry.create_registry()


def test_failure_metrics_increment_on_causality_breach(
    registry: CollectorRegistry,
) -> None:
    service = TrustGateSuiteService(tolerance_profile="causality")
    manifest = _build_candidate_manifest(
        leakage_score=0.15,
        equity_drift=0.03,
        sharpe_ratio=-0.8,
    )

    summary = service.run(
        candidate_manifest=manifest,
        config_hash="cfg-telemetry-fail",
        registry=registry,
    )

    assert summary.status == "fail"
    failure_value = registry.get_sample_value(
        "trust_gate_failure",
        labels={"gate": "causality", "profile": "causality"},
    )
    assert failure_value == pytest.approx(1.0)
    block = summary.manifest_block()
    assert block["tolerance_profile_version"]
    assert block["tolerance_profile_hash"]


def test_missing_profile_emits_config_error_metric(registry: CollectorRegistry) -> None:
    service = TrustGateSuiteService(tolerance_profile="missing-profile")

    with pytest.raises(ToleranceConfigError):
        service.run(candidate_manifest=_build_candidate_manifest(), registry=registry)

    config_error_value = registry.get_sample_value(
        "trust_gate_config_error",
        labels={
            "gate": "causality",
            "profile": "missing-profile",
            "reason": "not_found",
        },
    )
    assert config_error_value == pytest.approx(1.0)
