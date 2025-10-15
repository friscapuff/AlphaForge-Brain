"""Journaling artifact validation trust gate (Phase 016)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from services.audit.governance_logger import log_journaling_validation_failure
from services.hashing import hash_enriched_journaling_payload

from ..baseline import GateBaseline, TrustGateBaseline
from ..config_loader import ToleranceProfile
from ..models import TrustGateResult
from .base import build_result

_EXPECTED_SCHEMA_VERSION = "2025.10.16"
_REQUIRED_ARTIFACT = "completed_trades.json"
_WAIVER_REF = "journaling.artifact.required"


def _resolve_gate(baseline: TrustGateBaseline) -> GateBaseline:
    try:
        return baseline.gate("journaling")
    except KeyError:
        return GateBaseline(
            name="journaling",
            status="pass",
            artifact=None,
            sha256=None,
            correlation_id=None,
            metrics={},
        )


def _normalise_manifest_artifacts(
    manifest: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    if not isinstance(manifest, Mapping):
        return []
    raw = manifest.get("artifacts", [])
    if isinstance(raw, Sequence):
        entries: list[Mapping[str, Any]] = []
        for entry in raw:
            if not isinstance(entry, Mapping):
                continue
            path = entry.get("path") or entry.get("name")
            if isinstance(path, str):
                normalised = path.replace("\\", "/")
                if "zz_artifacts/journaling" in normalised:
                    entries.append(entry)
        return entries
    return []


def _resolve_run_id(manifest: Mapping[str, Any] | None) -> str:
    if isinstance(manifest, Mapping):
        run_id = manifest.get("run_id")
        if isinstance(run_id, str):
            return run_id
        run_section = manifest.get("run")
        if isinstance(run_section, Mapping):
            candidate = run_section.get("id") or run_section.get("run_id")
            if isinstance(candidate, str):
                return candidate
    return "unknown"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_snapshots(snapshot_dir: Path) -> list[Mapping[str, Any]]:
    snapshots: list[Mapping[str, Any]] = []
    if not snapshot_dir.exists() or not snapshot_dir.is_dir():
        return snapshots
    for child in sorted(snapshot_dir.glob("*.json")):
        try:
            loaded = _load_json(child)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(loaded, Mapping):
            snapshots.append(loaded)
    return snapshots


def _load_reasons(reasons_path: Path) -> list[Mapping[str, Any]]:
    if not reasons_path.exists():
        return []
    try:
        payload = _load_json(reasons_path)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    return []


def _compute_signature(
    *,
    run_id: str,
    schema_version: str,
    trades_path: Path,
) -> str | None:
    try:
        trades_payload = _load_json(trades_path)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(trades_payload, list):
        return None

    run_dir = trades_path.parent
    snapshots_dir = run_dir / "snapshots"
    reasons_path = run_dir / "reasons.json"

    payload = {
        "run_id": run_id,
        "schema_version": schema_version,
        "completed_trades": trades_payload,
        "snapshots": _load_snapshots(snapshots_dir),
        "reasons": _load_reasons(reasons_path),
    }
    return hash_enriched_journaling_payload(payload)


def evaluate(
    *,
    baseline: TrustGateBaseline,
    candidate_manifest: Mapping[str, Any] | None = None,
    tolerance_profile: ToleranceProfile | None = None,
    run_id: str | None = None,
) -> TrustGateResult:
    gate = _resolve_gate(baseline)
    manifest = candidate_manifest if isinstance(candidate_manifest, Mapping) else {}

    journaling_artifacts = _normalise_manifest_artifacts(manifest)
    artifact_index = {
        str(entry.get("name") or Path(str(entry.get("path", ""))).name): entry
        for entry in journaling_artifacts
    }

    gate_defaults = {}
    if isinstance(baseline, TrustGateBaseline):  # pragma: no branch - baseline type
        gate_defaults = {
            "expected_schema_version": gate.metrics.get("expected_schema_version"),
            "required_artifacts": gate.metrics.get("required_artifacts"),
        }

    tolerance_metadata = tolerance_profile.metadata if tolerance_profile else {}
    tolerance_gate_defaults = (
        tolerance_metadata.get("gate_defaults", {}).get("journaling", {})
        if isinstance(tolerance_metadata, Mapping)
        else {}
    )

    expected_schema_version = (
        tolerance_gate_defaults.get("expected_schema_version")
        or gate_defaults.get("expected_schema_version")
        or _EXPECTED_SCHEMA_VERSION
    )
    required_artifacts = tuple(
        tolerance_gate_defaults.get("required_artifacts")
        or gate_defaults.get("required_artifacts")
        or (_REQUIRED_ARTIFACT,)
    )

    metrics: dict[str, object] = {
        "artifacts_found": len(journaling_artifacts),
        "expected_schema_version": expected_schema_version,
        "manifest_schema_version": None,
        "schema_version_ok": False,
        "hash_match": False,
    }
    diagnostics: dict[str, object] = {}
    missing: list[str] = []
    trades_path: Path | None = None
    resolved_run_id = run_id or _resolve_run_id(manifest)

    artifact_entry = artifact_index.get(_REQUIRED_ARTIFACT)
    if artifact_entry is None:
        missing.append("completed_trades")
    else:
        raw_schema = artifact_entry.get("schema_version")
        schema_version = raw_schema if isinstance(raw_schema, str) else None
        metrics["manifest_schema_version"] = schema_version
        metrics["schema_version_ok"] = schema_version == expected_schema_version

        canonical_hash = artifact_entry.get("canonical_hash")
        canonical_hash_str = (
            canonical_hash
            if isinstance(canonical_hash, str) and canonical_hash
            else None
        )

        path_value = artifact_entry.get("path")
        if isinstance(path_value, str):
            candidate_path = Path(path_value)
            trades_path = (
                candidate_path
                if candidate_path.is_absolute()
                else (Path.cwd() / candidate_path)
            )
        if schema_version != expected_schema_version:
            diagnostics.setdefault("schema_mismatch", schema_version)
        if trades_path is None or not trades_path.exists():
            missing.append("completed_trades")
        else:
            computed_signature = _compute_signature(
                run_id=resolved_run_id,
                schema_version=schema_version or expected_schema_version,
                trades_path=trades_path,
            )
            if computed_signature:
                metrics["computed_signature"] = computed_signature
            if canonical_hash_str:
                metrics["manifest_signature"] = canonical_hash_str
            if computed_signature and canonical_hash_str:
                metrics["hash_match"] = computed_signature == canonical_hash_str
                if not metrics["hash_match"]:
                    diagnostics["hash_mismatch"] = True
            elif canonical_hash_str is None:
                diagnostics["missing_signature"] = True
            else:
                diagnostics["hash_computation_failed"] = True

    if missing:
        diagnostics["missing"] = sorted(set(missing))

    status = (
        "pass" if metrics["schema_version_ok"] and metrics["hash_match"] else "fail"
    )
    waiver_ref = _WAIVER_REF if status == "fail" else None
    tolerance_name = (
        tolerance_profile.profile_id
        if tolerance_profile is not None
        else baseline.tolerance_profile
    )

    tolerance_payload: dict[str, object] = {
        "required_artifacts": list(required_artifacts),
        "expected_schema_version": expected_schema_version,
        "waiver_reference": _WAIVER_REF,
    }
    enforcement_flag = tolerance_gate_defaults.get("enforce_manifest_signature")
    if enforcement_flag is not None:
        tolerance_payload["enforce_manifest_signature"] = bool(enforcement_flag)

    result = build_result(
        gate=gate,
        status=status,
        metrics=metrics,
        diagnostics=diagnostics,
        tolerance=tolerance_payload,
    )
    if waiver_ref:
        result = replace(result, waiver_ref=waiver_ref)
        retention_pointer: Path
        if trades_path is not None and trades_path.exists():
            retention_pointer = trades_path.parent
        else:
            retention_pointer = Path("zz_artifacts/journaling") / resolved_run_id
        log_journaling_validation_failure(
            run_id=resolved_run_id,
            diagnostics=diagnostics,
            tolerance_profile=tolerance_name,
            waiver_ref=waiver_ref,
            retention_pointer=retention_pointer,
        )
    return result
