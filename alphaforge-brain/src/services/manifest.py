"""Manifest writer (T043).

Builds a RunManifest from artifacts and run configuration.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from ..models.manifest import ArtifactDescriptor, RunManifest, TrustGateManifest
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
    metadata: Mapping[Path | str, Mapping[str, str]] | None = None,
) -> list[ArtifactDescriptor]:
    metadata_lookup: dict[str, Mapping[str, str]] = {}
    if metadata:
        for key, value in metadata.items():
            path_obj = Path(key)
            try:
                normalized_key = str(path_obj.resolve())
            except FileNotFoundError:
                normalized_key = str(path_obj)
            metadata_lookup[normalized_key] = dict(value)

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
        metadata_entry = None
        if metadata_lookup:
            resolved_key = str(p.resolve())
            metadata_entry = metadata_lookup.get(resolved_key)
            if metadata_entry is None:
                metadata_entry = metadata_lookup.get(str(p))
        artifacts.append(
            ArtifactDescriptor(
                name=p.name,
                path=descriptor_path,
                content_hash=_file_sha256(p),
                mime_type=None,
                schema_version=(
                    str(metadata_entry["schema_version"])
                    if metadata_entry and "schema_version" in metadata_entry
                    else None
                ),
                canonical_hash=(
                    str(metadata_entry["canonical_hash"])
                    if metadata_entry and "canonical_hash" in metadata_entry
                    else None
                ),
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
    trust_gate: TrustGateManifest | None = None,
    artifact_metadata: Mapping[Path | str, Mapping[str, str]] | None = None,
) -> RunManifest:
    artifacts = collect_artifacts(
        artifact_paths,
        run_root=run_root,
        validation_artifacts=validation_artifacts,
        metadata=artifact_metadata,
    )
    return RunManifest.from_run_config(run_id, config, artifacts, trust_gate)


__all__ = ["build_manifest", "collect_artifacts"]
