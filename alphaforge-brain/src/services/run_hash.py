from __future__ import annotations

from collections.abc import Iterable

from src.models.manifest import ArtifactDescriptor, compute_composite_hash_from
from src.models.run_config import RunConfig


def compute_run_hash(config: RunConfig, artifacts: Iterable[ArtifactDescriptor]) -> str:
    """Compute a deterministic run hash from config signature and artifacts.

    Inputs:
    - config: RunConfig with .deterministic_signature()
    - artifacts: iterable of ArtifactDescriptor

    The hash is stable to ordering of artifacts; artifacts are reduced to a
    canonical list of {name, path, content_hash} sorted by name.
    """
    cfg_sig = config.deterministic_signature()
    return compute_composite_hash_from(cfg_sig, list(artifacts))


__all__ = ["compute_run_hash"]
