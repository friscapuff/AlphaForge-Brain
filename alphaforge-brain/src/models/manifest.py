"""Run manifest & artifact descriptors.

T031 - Manifest models

Purpose:
* Provide a canonical, hashable manifest of all artifacts emitted by a run
* Reference configuration signature for provenance & reproducibility
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from pydantic import Field, model_validator

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
        parts = [self.config_signature]
        for a in sorted(self.artifacts, key=lambda x: x.name):
            parts.append(f"{a.name}:{a.content_hash}:{a.path}")
        blob = "|".join(parts)
        return sha256(blob.encode("utf-8")).hexdigest()

    @classmethod
    def from_run_config(
        cls, run_id: str, config: RunConfig, artifacts: list[ArtifactDescriptor]
    ) -> RunManifest:
        sig = config.deterministic_signature()
        return cls(run_id=run_id, config_signature=sig, artifacts=artifacts)


__all__ = ["ArtifactDescriptor", "RunManifest"]
