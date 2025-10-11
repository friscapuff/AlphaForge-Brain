"""Test fixtures for the Trust Gate framework.

These helpers expose deterministic baseline artifacts, digests, and dataset
references so contract and integration tests can assert trust gate behaviour
without duplicating JSON fixtures inline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Unable to locate repository root for trust gate fixtures")


REPO_ROOT = _repo_root()
BASELINE_DIR = REPO_ROOT / "artifacts" / "trust_gates" / "baselines" / "v1"
TOLERANCE_PROFILE_PATH = (
    REPO_ROOT / "configs" / "trust_gates" / "tolerances" / "institutional_default.yaml"
)


@dataclass(frozen=True)
class GateBaseline:
    """Canonical information for a single trust gate."""

    name: str
    sha256: str
    artifact: Path
    correlation_id: str


@dataclass(frozen=True)
class TrustGateBaselineFixture:
    """Aggregate baseline metadata used across trust gate tests."""

    config_hash: str
    tolerance_profile_name: str
    manifest_snapshot: Mapping[str, object]
    artifact_hashes: Mapping[str, object]
    gates: Dict[str, GateBaseline]
    dataset_hashes: Dict[str, str]

    def gate(self, name: str) -> GateBaseline:
        """Return canonical details for the requested gate.

        Raises:
            KeyError: If the gate name is unknown in the baseline.
        """

        return self.gates[name]


def _load_json(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_manifest_snapshot() -> Mapping[str, object]:
    """Load the canonical golden-run manifest snapshot."""

    return _load_json(BASELINE_DIR / "manifest_snapshot.json")


@lru_cache(maxsize=1)
def load_artifact_hashes() -> Mapping[str, object]:
    """Load the canonical artifact hash mapping for the golden run."""

    return _load_json(BASELINE_DIR / "artifact_hashes.json")


@lru_cache(maxsize=1)
def load_trust_gate_baseline() -> TrustGateBaselineFixture:
    """Return the aggregated baseline fixture for test consumption."""

    manifest = load_manifest_snapshot()
    hashes = load_artifact_hashes()

    run = manifest["run"]
    trust_gate = run["trust_gate"]

    gates: Dict[str, GateBaseline] = {}
    for gate in trust_gate["gates"]:
        gates[gate["name"]] = GateBaseline(
            name=gate["name"],
            sha256=gate["sha256"],
            artifact=REPO_ROOT / gate["artifact"],
            correlation_id=gate["correlation_id"],
        )

    dataset_hashes = {
        key: value["sha256"] for key, value in hashes.get("datasets", {}).items()
    }

    return TrustGateBaselineFixture(
        config_hash=run["config_hash"],
        tolerance_profile_name=run["tolerance_profile"],
        manifest_snapshot=manifest,
        artifact_hashes=hashes,
        gates=gates,
        dataset_hashes=dataset_hashes,
    )


def load_tolerance_profile_text() -> str:
    """Return the raw YAML text for the institutional tolerance profile."""

    return TOLERANCE_PROFILE_PATH.read_text(encoding="utf-8")


def baseline_signature_path() -> Path:
    """Path to the detached signature placeholder for the baseline."""

    return BASELINE_DIR / "baseline.signature"
