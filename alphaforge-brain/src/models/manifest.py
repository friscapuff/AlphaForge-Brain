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


class TrustGateGateDescriptor(BaseModelStrict):
    name: str
    status: str
    artifact: str | None = None
    correlation_id: str | None = None
    waiver_ref: str | None = None
    duration_ms: int | None = None


class TrustGateManifest(BaseModelStrict):
    schema_version: str = Field(default="trust_gates.v1")
    status: str
    suite_id: str
    executed_at: datetime
    suite_version: int = 1
    config_hash: str
    tolerance_profile: str | None = None
    runtime_ms: int | None = None
    gates: list[TrustGateGateDescriptor] = Field(default_factory=list)
    signature_path: str | None = None
    report_path: str | None = None
    enabled_gates: list[str] = Field(default_factory=list)


class RunManifest(BaseModelStrict):  # FR-030..FR-034
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    config_signature: str
    artifacts: list[ArtifactDescriptor] = Field(default_factory=list)
    composite_hash: str | None = Field(
        default=None, description="Hash over artifacts list + config signature"
    )
    trust_gate: TrustGateManifest | None = None

    @model_validator(mode="after")
    def _ensure_hash(self) -> RunManifest:
        if self.composite_hash is None:
            self.__dict__["composite_hash"] = self.compute_composite_hash()
        return self

    def compute_composite_hash(self) -> str:
        return compute_composite_hash_from(
            self.config_signature,
            self.artifacts,
            self.trust_gate,
        )

    @classmethod
    def from_run_config(
        cls,
        run_id: str,
        config: RunConfig,
        artifacts: list[ArtifactDescriptor],
        trust_gate: TrustGateManifest | None = None,
    ) -> RunManifest:
        sig = config.deterministic_signature()
        return cls(
            run_id=run_id,
            config_signature=sig,
            artifacts=artifacts,
            trust_gate=trust_gate,
        )


def compute_composite_hash_from(
    config_signature: str,
    artifacts: list[ArtifactDescriptor],
    trust_gate: TrustGateManifest | None = None,
) -> str:
    # Stable, order-independent canonical payload
    reduced = [
        {"name": a.name, "path": a.path, "content_hash": a.content_hash}
        for a in artifacts
    ]
    reduced.sort(key=lambda d: d["name"])  # order independence
    payload: dict[str, object] = {
        "config_signature": config_signature,
        "artifacts": reduced,
    }
    if trust_gate is not None:
        tg_payload = {
            "status": trust_gate.status,
            "suite_id": trust_gate.suite_id,
            "suite_version": trust_gate.suite_version,
            "runtime_ms": trust_gate.runtime_ms,
            "signature_path": trust_gate.signature_path,
            "report_path": trust_gate.report_path,
            "gates": [
                {
                    "name": gate.name,
                    "status": gate.status,
                    "waiver_ref": gate.waiver_ref,
                    "correlation_id": gate.correlation_id,
                }
                for gate in trust_gate.gates
            ],
        }
        payload["trust_gate"] = tg_payload
    return sha256_hex(canonical_json(payload).encode("utf-8"))


__all__ = [
    "ArtifactDescriptor",
    "TrustGateManifest",
    "TrustGateGateDescriptor",
    "RunManifest",
    "compute_composite_hash_from",
]
