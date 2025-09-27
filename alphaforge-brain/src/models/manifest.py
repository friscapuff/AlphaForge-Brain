"""Run manifest & artifact descriptors.

T031 - Manifest models

Purpose:
* Provide a canonical, hashable manifest of all artifacts emitted by a run
* Reference configuration signature for provenance & reproducibility
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field, model_validator

from ..infra.utils.hash import canonical_json, sha256_hex
from .base import BaseModelStrict
from .run_config import RunConfig


class ArtifactDescriptor(BaseModelStrict):  # FR-030..FR-034 (reporting provenance)
    name: str
    path: str
    content_hash: str = Field(description="SHA-256 of artifact content")
    mime_type: str | None = None


class RunManifest(BaseModelStrict):  # FR-030..FR-034
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    config_signature: str
    artifacts: list[ArtifactDescriptor] = Field(default_factory=list)
    composite_hash: str | None = Field(
        default=None, description="Hash over artifacts list + config signature"
    )

    @model_validator(mode="after")
    def _ensure_hash(self) -> RunManifest:
        if self.composite_hash is None:
            self.__dict__["composite_hash"] = self.compute_composite_hash()
        return self

    def compute_composite_hash(self) -> str:
        return compute_composite_hash_from(self.config_signature, self.artifacts)

    @classmethod
    def from_run_config(
        cls, run_id: str, config: RunConfig, artifacts: list[ArtifactDescriptor]
    ) -> RunManifest:
        sig = config.deterministic_signature()
        return cls(run_id=run_id, config_signature=sig, artifacts=artifacts)


def compute_composite_hash_from(
    config_signature: str, artifacts: list[ArtifactDescriptor]
) -> str:
    # Stable, order-independent canonical payload
    reduced = [
        {"name": a.name, "path": a.path, "content_hash": a.content_hash}
        for a in artifacts
    ]
    reduced.sort(key=lambda d: d["name"])  # order independence
    payload = {"config_signature": config_signature, "artifacts": reduced}
    return sha256_hex(canonical_json(payload).encode("utf-8"))


__all__ = ["ArtifactDescriptor", "RunManifest", "compute_composite_hash_from"]
