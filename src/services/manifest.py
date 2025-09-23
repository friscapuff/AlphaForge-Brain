"""Manifest writer (T043).

Builds a RunManifest from artifacts and run configuration.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from ..models.manifest import ArtifactDescriptor, RunManifest
from ..models.run_config import RunConfig


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts(paths: Iterable[Path]) -> list[ArtifactDescriptor]:
    artifacts: list[ArtifactDescriptor] = []
    for p in paths:
        if not p.is_file():
            continue
        artifacts.append(
            ArtifactDescriptor(
                name=p.name,
                path=str(p),
                content_hash=_file_sha256(p),
                mime_type=None,
            )
        )
    return artifacts


def build_manifest(run_id: str, config: RunConfig, artifact_paths: Iterable[Path]) -> RunManifest:
    artifacts = collect_artifacts(artifact_paths)
    return RunManifest.from_run_config(run_id, config, artifacts)

__all__ = ["build_manifest", "collect_artifacts"]
