"""Repository helpers for loading sweep manifests and building status payloads."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from models.manifest import (
    SweepCombination,
    SweepManifest,
    SweepTrustGateEvidence,
)

from .orchestrator import DEFAULT_SWEEP_ROOT

ENV_SWEEP_ROOT = "ALPHAFORGEB_SWEEP_ROOT"


def _default_sweep_root() -> Path:
    env_value = os.getenv(ENV_SWEEP_ROOT)
    if env_value:
        return Path(env_value)
    return DEFAULT_SWEEP_ROOT


@dataclass(slots=True)
class SweepManifestRecord:
    """Materialized sweep manifest with associated paths."""

    sweep_id: str
    manifest: SweepManifest
    path: Path


def load_manifest(
    sweep_id: str, *, storage_root: Path | None = None
) -> SweepManifestRecord:
    """Load the sweep manifest for *sweep_id* from disk."""

    manifest_path = _manifest_path(sweep_id, storage_root)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Sweep manifest not found for id={sweep_id}")
    raw_text = manifest_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Manifest JSON is invalid for sweep {sweep_id}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"Manifest payload malformed for sweep {sweep_id}")
    manifest = SweepManifest.from_storage_dict(payload)
    return SweepManifestRecord(sweep_id=sweep_id, manifest=manifest, path=manifest_path)


def manifest_to_status(
    record: SweepManifestRecord,
    *,
    metrics_namespace: str = "alphaforge.sweeps",
) -> dict[str, Any]:
    """Convert a manifest record into API response payload."""

    manifest = record.manifest
    combinations_payload = _serialize_combinations(manifest.combinations)
    aggregates_source = cast(dict[str, int | float | None], manifest.aggregates)
    aggregates_payload = {
        key: value for key, value in aggregates_source.items() if value is not None
    }
    trust_gates_payload = _serialize_trust_gates(manifest.trust_gates)
    tickers_payload = [
        {
            "ticker": ticker.ticker,
            "combination_cap": ticker.combination_cap,
            "cap_status": ticker.cap_status.value,
            "data_quality_status": ticker.data_quality_status.value,
            "variance_metrics": dict(ticker.variance_metrics),
            "manifest_path": ticker.manifest_path,
            "partial_execution_reason": ticker.partial_execution_reason,
        }
        for ticker in manifest.tickers
    ]
    telemetry_reference = {
        "manifest_path": record.path.as_posix(),
        "metrics_namespace": metrics_namespace,
    }
    status_payload: dict[str, Any] = {
        "sweep_id": manifest.sweep_id,
        "status": manifest.status.value,
        "combination_cap": manifest.combination_cap,
        "submitted_at": manifest.submitted_at.isoformat(),
        "completed_at": (
            manifest.completed_at.isoformat() if manifest.completed_at else None
        ),
        "initiator": manifest.initiator,
        "combinations": combinations_payload,
        "aggregates": aggregates_payload,
        "telemetry_reference": telemetry_reference,
        "tickers": tickers_payload,
        "derived_metrics": dict(manifest.derived_metrics),
        "notes": list(manifest.notes),
        "trust_gates": trust_gates_payload,
    }
    return status_payload


def get_sweep_status(
    sweep_id: str,
    *,
    storage_root: Path | None = None,
    metrics_namespace: str = "alphaforge.sweeps",
) -> dict[str, Any]:
    """Convenience helper to load a sweep manifest and return its status payload."""

    record = load_manifest(sweep_id, storage_root=storage_root)
    return manifest_to_status(record, metrics_namespace=metrics_namespace)


def list_sweeps(storage_root: Path | None = None) -> list[str]:
    """Return sorted list of sweep ids with persisted manifests."""

    root = storage_root or _default_sweep_root()
    if not root.exists():
        return []
    sweeps: list[str] = []
    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "manifest.json"
        if manifest_path.exists():
            sweeps.append(candidate.name)
    sweeps.sort()
    return sweeps


def _serialize_combinations(
    combinations: Sequence[SweepCombination],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for combo in combinations:
        payload.append(
            {
                "combination_id": combo.combination_id,
                "parameters": [
                    {
                        "name": assignment.name,
                        "value": assignment.value,
                    }
                    for assignment in combo.parameters
                ],
                "run_hash": combo.run_hash,
                "status": combo.status.value,
                "started_at": (
                    combo.started_at.isoformat() if combo.started_at else None
                ),
                "completed_at": (
                    combo.completed_at.isoformat() if combo.completed_at else None
                ),
                "duration_ms": combo.duration_ms,
                "trust_gate_summary": (
                    combo.trust_gate_summary.model_dump(mode="json")
                    if combo.trust_gate_summary is not None
                    else None
                ),
            }
        )
    return payload


def _serialize_trust_gates(trust_gates: SweepTrustGateEvidence) -> dict[str, Any]:
    return trust_gates.model_dump(mode="json", exclude_none=True)


def _manifest_path(sweep_id: str, storage_root: Path | None) -> Path:
    root = storage_root or _default_sweep_root()
    return root / sweep_id / "manifest.json"


__all__ = [
    "SweepManifestRecord",
    "get_sweep_status",
    "list_sweeps",
    "load_manifest",
    "manifest_to_status",
]
