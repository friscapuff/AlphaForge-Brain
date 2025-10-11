from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from ..models.manifest import (
    ArtifactDescriptor,
    TrustGateManifest,
    compute_composite_hash_from,
)
from ..models.run_config import RunConfig


def compute_run_hash(
    config: RunConfig,
    artifacts: Iterable[ArtifactDescriptor],
    trust_gate: TrustGateManifest | None = None,
) -> str:
    """Compute a deterministic run hash from config signature and artifacts.

    Inputs:
    - config: RunConfig with .deterministic_signature()
    - artifacts: iterable of ArtifactDescriptor

    The hash is stable to ordering of artifacts; artifacts are reduced to a
    canonical list of {name, path, content_hash} sorted by name.
    """
    cfg_sig = config.deterministic_signature()
    artifact_list: list[ArtifactDescriptor] = list(artifacts)
    return cast(str, compute_composite_hash_from(cfg_sig, artifact_list, trust_gate))


__all__ = ["compute_run_hash"]
