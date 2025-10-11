"""Baseline artifact helpers for the trust gate framework."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping, Optional


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
    artifact: Optional[str]
    sha256: Optional[str]
    correlation_id: Optional[str]
    metrics: Mapping[str, object]


@dataclass(frozen=True)
class TrustGateBaseline:
    """Aggregate baseline metadata for the trust gate suite."""

    config_hash: str
    tolerance_profile: str
    manifest_snapshot: Mapping[str, object]
    artifact_hashes: Mapping[str, object]
    gates: Dict[str, GateBaseline]
    dataset_hashes: Dict[str, str]

    def gate(self, name: str) -> GateBaseline:
        return self.gates[name]


def _load_json(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_baseline() -> TrustGateBaseline:
    manifest = _load_json(MANIFEST_PATH)
    artifact_hashes = _load_json(ARTIFACT_HASHES_PATH)

    run = manifest["run"]
    trust_gate = run["trust_gate"]

    gates: Dict[str, GateBaseline] = {}
    for entry in trust_gate["gates"]:
        gates[entry["name"]] = GateBaseline(
            name=entry["name"],
            status=entry.get("status", "unknown"),
            artifact=entry.get("artifact"),
            sha256=entry.get("sha256"),
            correlation_id=entry.get("correlation_id"),
            metrics=entry.get("metrics", {}),
        )

    datasets = {
        key: value.get("sha256")
        for key, value in artifact_hashes.get("datasets", {}).items()
    }

    return TrustGateBaseline(
        config_hash=run["config_hash"],
        tolerance_profile=run["tolerance_profile"],
        manifest_snapshot=manifest,
        artifact_hashes=artifact_hashes,
        gates=gates,
        dataset_hashes=datasets,
    )
