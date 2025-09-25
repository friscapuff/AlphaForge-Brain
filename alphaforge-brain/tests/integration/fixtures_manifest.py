"""Manifest replay fixture & helpers (FR-024: deterministic replay).

Provides utilities for tests to:
- Load manifest for a given run hash
- Extract artifact hashes and compare between runs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from domain.schemas.artifacts import ArtifactEntry, ArtifactManifest

ARTIFACTS_DIR = Path("artifacts")


def load_manifest(run_hash: str) -> dict[str, Any]:
    path = ARTIFACTS_DIR / run_hash / "manifest.json"
    if not path.exists():  # pragma: no cover simple guard
        raise FileNotFoundError(f"manifest not found for run {run_hash}")
    return json.loads(path.read_text("utf-8"))


def artifact_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    files = manifest.get("files", [])
    out: dict[str, str] = {}
    if isinstance(files, list):
        for f in files:
            if isinstance(f, dict) and {"name", "sha256"}.issubset(f.keys()):
                out[f["name"]] = f["sha256"]
    return out


@pytest.fixture()
def manifest_loader():
    """Load an ArtifactManifest (writer schema) and perform basic integrity checks.

    Returns a callable (run_hash: str) -> ArtifactManifest.
    """

    def _load(run_hash: str) -> ArtifactManifest:
        path = ARTIFACTS_DIR / run_hash / "manifest.json"
        if not path.exists():  # pragma: no cover - guard
            raise FileNotFoundError(f"manifest not found for run {run_hash}")
        data = json.loads(path.read_text("utf-8"))
        # Map file entries to ArtifactEntry list expected by ArtifactManifest for hash recompute
        files = data.get("files", []) if isinstance(data, dict) else []
        entries: list[ArtifactEntry] = []
        for f in files:
            if not isinstance(f, dict):
                continue
            try:
                entries.append(
                    ArtifactEntry(
                        name=f["name"],
                        kind=f.get("kind", "unknown"),
                        sha256=f["sha256"],
                        bytes=f.get("size", 0),
                    )
                )
            except Exception:
                continue
        am = ArtifactManifest(
            entries=entries,
            chain_prev=data.get("chain_prev"),
            data_hash=data.get("data_hash"),
            calendar_id=data.get("calendar_id"),
            symbol=data.get("symbol"),
            timeframe=data.get("timeframe"),
        )
        recomputed = am.canonical_hash()
        # Compare against stored manifest_hash if present
        stored = data.get("manifest_hash")
        if isinstance(stored, str):
            assert stored == recomputed, "Manifest hash mismatch (corruption suspected)"
        # Ensure uniqueness of names already enforced in model validator
        return am

    return _load


__all__ = ["artifact_hashes", "load_manifest", "manifest_loader"]
