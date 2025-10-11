"""Baseline artifact helpers for the trust gate framework."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence, cast


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Unable to locate repository root for trust gate baseline")


REPO_ROOT = _repo_root()
BASELINE_DIR = REPO_ROOT / "artifacts" / "trust_gates" / "baselines" / "v1"
MANIFEST_PATH = BASELINE_DIR / "manifest_snapshot.json"
ARTIFACT_HASHES_PATH = BASELINE_DIR / "artifact_hashes.json"


@dataclass(frozen=True)
class GateBaseline:
    """Canonical information for a gate captured in the baseline manifest."""

    name: str
    status: str
    artifact: str | None
    sha256: str | None
    correlation_id: str | None
    metrics: Mapping[str, object]


@dataclass(frozen=True)
class TrustGateBaseline:
    """Aggregate baseline metadata for the trust gate suite."""

    config_hash: str
    tolerance_profile: str
    manifest_snapshot: Mapping[str, object]
    artifact_hashes: Mapping[str, object]
    gates: dict[str, GateBaseline]
    dataset_hashes: dict[str, str]

    def gate(self, name: str) -> GateBaseline:
        return self.gates[name]


def _load_json(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise RuntimeError(f"Baseline file {path} does not contain an object")
    return cast(Mapping[str, object], data)


@lru_cache(maxsize=1)
def load_baseline() -> TrustGateBaseline:
    manifest = _load_json(MANIFEST_PATH)
    artifact_hashes = _load_json(ARTIFACT_HASHES_PATH)

    run_obj = manifest.get("run")
    if not isinstance(run_obj, Mapping):
        raise RuntimeError("Baseline manifest missing run section")
    run = cast(Mapping[str, object], run_obj)

    trust_gate_obj = run.get("trust_gate")
    if not isinstance(trust_gate_obj, Mapping):
        raise RuntimeError("Baseline manifest missing trust_gate section")
    trust_gate = cast(Mapping[str, object], trust_gate_obj)

    gates: dict[str, GateBaseline] = {}
    raw_gates = trust_gate.get("gates", [])
    if isinstance(raw_gates, Sequence):
        for raw_entry in raw_gates:
            if not isinstance(raw_entry, Mapping):
                continue
            entry = cast(Mapping[str, object], raw_entry)
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            status = entry.get("status", "unknown")
            status_str = status if isinstance(status, str) else "unknown"
            artifact = entry.get("artifact")
            artifact_str = artifact if isinstance(artifact, str) else None
            sha256 = entry.get("sha256")
            sha_str = sha256 if isinstance(sha256, str) else None
            correlation = entry.get("correlation_id")
            correlation_str = correlation if isinstance(correlation, str) else None
            metrics_obj = entry.get("metrics", {})
            metrics_data: Mapping[str, object]
            if isinstance(metrics_obj, Mapping):
                metrics_data = cast(Mapping[str, object], metrics_obj)
            else:
                metrics_data = cast(Mapping[str, object], {})

            gates[name] = GateBaseline(
                name=name,
                status=status_str,
                artifact=artifact_str,
                sha256=sha_str,
                correlation_id=correlation_str,
                metrics=metrics_data,
            )

    datasets: dict[str, str] = {}
    datasets_obj = artifact_hashes.get("datasets", {})
    if isinstance(datasets_obj, Mapping):
        for key, value in datasets_obj.items():
            if not isinstance(key, str) or not isinstance(value, Mapping):
                continue
            sha_value = value.get("sha256")
            if isinstance(sha_value, str):
                datasets[key] = sha_value

    config_hash = run.get("config_hash")
    if not isinstance(config_hash, str):
        raise RuntimeError("Baseline run config_hash missing or invalid")

    tolerance_profile = run.get("tolerance_profile")
    if not isinstance(tolerance_profile, str):
        raise RuntimeError("Baseline run tolerance_profile missing or invalid")

    return TrustGateBaseline(
        config_hash=config_hash,
        tolerance_profile=tolerance_profile,
        manifest_snapshot=manifest,
        artifact_hashes=artifact_hashes,
        gates=gates,
        dataset_hashes=datasets,
    )
