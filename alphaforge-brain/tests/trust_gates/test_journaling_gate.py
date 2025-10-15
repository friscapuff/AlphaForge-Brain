"""Regression tests for the journaling trust gate (Phase 016 / T019)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

import pytest
from prometheus_client import CollectorRegistry
from services.hashing import hash_enriched_journaling_payload
from services.trust_gates import telemetry
from services.trust_gates.suite_service import TrustGateSuiteService

from tests.fixtures.trust_gates import load_manifest_snapshot


def _baseline_manifest() -> dict[str, Any]:
    return copy.deepcopy(load_manifest_snapshot())  # type: ignore[return-value]


def _prune_journaling_artifacts(manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = manifest.setdefault("artifacts", [])
    if isinstance(artifacts, list):
        manifest["artifacts"] = [
            entry
            for entry in artifacts
            if not (isinstance(entry, dict) and entry.get("group") == "journaling")
        ]
    run_section = manifest.setdefault("run", {})
    trust_gate_section = run_section.setdefault("trust_gate", {})
    gates = trust_gate_section.setdefault("gates", [])
    trust_gate_section["gates"] = [
        entry
        for entry in gates
        if not (isinstance(entry, dict) and entry.get("name") == "journaling")
    ]
    return manifest


def _with_journaling_artifacts(
    manifest: dict[str, Any], *, run_id: str, workspace: Path
) -> tuple[dict[str, Any], Path, str]:
    workspace_artifacts = workspace / "zz_artifacts" / "journaling" / run_id
    workspace_artifacts.mkdir(parents=True, exist_ok=True)
    completed_trades_path = workspace_artifacts / "completed_trades.json"

    trade_payload = [
        {
            "id": "trade-001",
            "symbol": "AAPL",
            "entry_ts": "2025-10-15T09:30:00Z",
            "exit_ts": "2025-10-15T15:45:00Z",
            "fills": [
                {
                    "order_id": "order-123",
                    "ts": "2025-10-15T09:31:00Z",
                    "price": 187.32,
                }
            ],
        }
    ]

    completed_trades_path.write_text(
        json.dumps(trade_payload, indent=2), encoding="utf-8"
    )

    manifest_with_run = manifest.setdefault("run", {})
    manifest_with_run["run_id"] = run_id
    trust_section = manifest_with_run.setdefault("trust_gate", {})
    gates_section = trust_section.setdefault("gates", [])
    gates_section[:] = [
        entry
        for entry in gates_section
        if not (isinstance(entry, Mapping) and entry.get("name") == "journaling")
    ]
    gates_section.append({"name": "journaling", "status": "pass"})

    artifacts = manifest.setdefault("artifacts", [])
    artifacts.append(
        {
            "group": "journaling",
            "name": "completed_trades.json",
            "path": str(completed_trades_path),
            "schema_version": "2025.10.16",
            "canonical_hash": hash_enriched_journaling_payload(
                {
                    "run_id": run_id,
                    "schema_version": "2025.10.16",
                    "completed_trades": trade_payload,
                    "snapshots": [],
                    "reasons": [],
                }
            ),
        }
    )
    return manifest, completed_trades_path, run_id


@pytest.fixture()
def registry() -> CollectorRegistry:
    return telemetry.create_registry()


def test_journaling_gate_fails_when_artifacts_missing(
    registry: CollectorRegistry,
) -> None:
    manifest = _prune_journaling_artifacts(_baseline_manifest())
    service = TrustGateSuiteService(tolerance_profile="institutional_default")

    summary = service.run(
        candidate_manifest=manifest,
        registry=registry,
        only=("journaling",),
        run_id="run-missing-journaling",
    )

    assert summary.status == "fail"
    assert summary.enabled_gates == ["journaling"]
    assert summary.runtime_ms is not None

    journaling_result = summary.results[0]
    assert journaling_result.name == "journaling"
    assert journaling_result.status == "fail"
    assert journaling_result.waiver_ref == "journaling.artifact.required"
    assert journaling_result.metrics.get("artifacts_found") == 0
    assert journaling_result.diagnostics.get("missing") == ["completed_trades"]

    failure_value = registry.get_sample_value(
        "trust_gate_failures_total",
        labels={"gate": "journaling", "profile": "institutional_default"},
    )
    assert failure_value == pytest.approx(1.0)

    reconciliation_value = registry.get_sample_value(
        "trust_gate_journaling_manifest_reconciliations_total",
        labels={"status": "fail", "profile": "institutional_default"},
    )
    assert reconciliation_value == pytest.approx(1.0)

    manifest_size_value = registry.get_sample_value(
        "trust_gate_manifest_payload_size_bytes",
        labels={"profile": "institutional_default"},
    )
    assert manifest_size_value is not None and manifest_size_value > 0

    manifest_block = summary.manifest_block()
    gates = manifest_block["gates"]
    journaling_gate = next(entry for entry in gates if entry["name"] == "journaling")
    assert journaling_gate["status"] == "fail"
    assert journaling_gate["waiver_ref"] == "journaling.artifact.required"
    assert journaling_gate["schema_version"] == "2025.10.16"
    assert journaling_gate.get("hash_match") is False
    assert journaling_gate.get("schema_version_ok") is False
    assert journaling_gate.get("diagnostics", {}).get("missing") == ["completed_trades"]
    assert "manifest_signature" not in journaling_gate
    assert journaling_gate.get("tolerance", {}).get("required_artifacts") == [
        "completed_trades.json"
    ]


def test_journaling_gate_logs_governance_event(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _prune_journaling_artifacts(_baseline_manifest())
    service = TrustGateSuiteService(tolerance_profile="institutional_default")

    captured: dict[str, Any] = {}

    def _fake_logger(
        *,
        run_id: str,
        diagnostics: Mapping[str, Any],
        tolerance_profile: str | None,
        waiver_ref: str | None,
        retention_pointer: Path | str,
        audit_path: Path | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        captured["run_id"] = run_id
        captured["diagnostics"] = dict(diagnostics)
        captured["tolerance_profile"] = tolerance_profile
        captured["waiver_ref"] = waiver_ref
        captured["retention_pointer"] = str(retention_pointer)

    monkeypatch.setattr(
        "services.trust_gates.gates.journaling.log_journaling_validation_failure",
        _fake_logger,
    )

    service.run(
        candidate_manifest=manifest,
        only=("journaling",),
        run_id="run-governance-log",
    )

    assert captured["run_id"] == "run-governance-log"
    assert captured["waiver_ref"] == "journaling.artifact.required"
    assert captured["tolerance_profile"]
    diagnostics = captured["diagnostics"]
    assert diagnostics["missing"] == ["completed_trades"]
    pointer_path = Path(captured["retention_pointer"])
    assert pointer_path.name == "run-governance-log"
    assert pointer_path.parent.name == "journaling"


def test_journaling_gate_passes_with_valid_artifacts(
    registry: CollectorRegistry, tmp_path: Path
) -> None:
    manifest = _prune_journaling_artifacts(_baseline_manifest())
    manifest, completed_trades_path, run_id = _with_journaling_artifacts(
        manifest, run_id="run-valid-journaling", workspace=tmp_path
    )

    service = TrustGateSuiteService(tolerance_profile="institutional_default")
    summary = service.run(
        candidate_manifest=manifest,
        registry=registry,
        only=("journaling",),
        run_id=run_id,
    )

    assert summary.status == "pass"
    result = summary.results[0]
    assert result.status == "pass"
    assert result.metrics.get("hash_match") is True
    assert result.metrics.get("manifest_signature")
    assert result.metrics.get("computed_signature")
    assert result.tolerance.get("expected_schema_version") == "2025.10.16"
    assert result.tolerance.get("waiver_reference") == "journaling.artifact.required"

    manifest_block = summary.manifest_block()
    journaling_gate = next(
        entry for entry in manifest_block["gates"] if entry["name"] == "journaling"
    )
    assert journaling_gate["hash_match"] is True
    assert journaling_gate["schema_version_ok"] is True
    assert journaling_gate["manifest_signature"] == result.metrics["manifest_signature"]
    assert journaling_gate["computed_signature"] == result.metrics["computed_signature"]

    reconciliation_value = registry.get_sample_value(
        "trust_gate_journaling_manifest_reconciliations_total",
        labels={"status": "pass", "profile": "institutional_default"},
    )
    assert reconciliation_value == pytest.approx(1.0)

    failure_value = registry.get_sample_value(
        "trust_gate_failures_total",
        labels={"gate": "journaling", "profile": "institutional_default"},
    )
    assert failure_value in (None, 0.0)

    manifest_size_value = registry.get_sample_value(
        "trust_gate_manifest_payload_size_bytes",
        labels={"profile": "institutional_default"},
    )
    assert manifest_size_value is not None and manifest_size_value > 0

    assert completed_trades_path.exists()
