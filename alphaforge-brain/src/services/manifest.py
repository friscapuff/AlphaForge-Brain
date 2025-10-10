"""Manifest writer (T043).

Builds a RunManifest from artifacts and run configuration.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.manifest import ArtifactDescriptor, RunManifest
from ..models.run_config import RunConfig

if TYPE_CHECKING:  # pragma: no cover - typing only import
    from .validation.manifest_v2 import ValidationArtifact


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts(
    paths: Iterable[Path],
    *,
    run_root: Path | None = None,
    validation_artifacts: Iterable[ValidationArtifact] | None = None,
) -> list[ArtifactDescriptor]:
    artifacts: list[ArtifactDescriptor] = []
    for p in paths:
        if not p.is_file():
            continue
        descriptor_path = str(p)
        if run_root is not None:
            try:
                descriptor_path = str(p.relative_to(run_root))
            except ValueError:
                descriptor_path = str(p)
        artifacts.append(
            ArtifactDescriptor(
                name=p.name,
                path=descriptor_path,
                content_hash=_file_sha256(p),
                mime_type=None,
            )
        )
    if validation_artifacts:
        seen_paths = {art.path for art in artifacts}
        for v in validation_artifacts:
            rel_path = v.path.as_posix()
            full_path = rel_path
            if run_root is not None:
                full_path = str(run_root / v.path)
            if full_path in seen_paths:
                continue
            artifacts.append(
                ArtifactDescriptor(
                    name=rel_path,
                    path=full_path,
                    content_hash=v.sha256,
                    mime_type=None,
                )
            )
            seen_paths.add(full_path)
    return artifacts


def build_manifest(
    run_id: str,
    config: RunConfig,
    artifact_paths: Iterable[Path],
    *,
    run_root: Path | None = None,
    validation_artifacts: Iterable[ValidationArtifact] | None = None,
) -> RunManifest:
    artifacts = collect_artifacts(
        artifact_paths,
        run_root=run_root,
        validation_artifacts=validation_artifacts,
    )
    return RunManifest.from_run_config(run_id, config, artifacts)


__all__ = ["build_manifest", "collect_artifacts"]
