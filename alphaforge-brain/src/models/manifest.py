"""Run and sweep manifest descriptors.

T031 - Manifest models

Purpose:
* Provide a canonical, hashable manifest of all artifacts emitted by a run
* Reference configuration signature for provenance & reproducibility
* Model sweep lineage artifacts for deterministic parameter sweeps (FR-004, FR-005)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, cast

from pydantic import Field, computed_field, model_validator

from infra.utils.hash import canonical_json, sha256_hex

from .base import BaseModelStrict
from .parameter_definition import ParameterDefinition, ParameterValue
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


class SweepCombinationStatus(str, Enum):
    """Lifecycle states for sweep combinations."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class SweepStatus(str, Enum):
    """Overall sweep lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SweepCapStatus(str, Enum):
    OK = "ok"
    HIT = "hit"
    WAIVED = "waived"


class SweepDataQualityStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"


class SweepTrustGateValidationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    CAUTION = "CAUTION"


class SweepParameterAssignment(BaseModelStrict):
    name: str
    value: ParameterValue


class SweepTrustGateSummary(BaseModelStrict):
    validation_status: SweepTrustGateValidationStatus = (
        SweepTrustGateValidationStatus.PASSED
    )
    failure_reason: str | None = None


class SweepTrustGateCheckpoint(BaseModelStrict):
    sanitized_parameters: dict[str, Any] | None = None
    data_quality_status: SweepDataQualityStatus = SweepDataQualityStatus.PASS
    cap_status: SweepCapStatus = SweepCapStatus.OK
    latency_ms: int | None = None
    notes: list[str] = Field(default_factory=list)


class SweepTrustGateEvidence(BaseModelStrict):
    payload_validation: SweepTrustGateCheckpoint | None = None
    normalization: SweepTrustGateCheckpoint | None = None
    orchestrator: SweepTrustGateCheckpoint | None = None
    manifest: SweepTrustGateCheckpoint | None = None


class SweepCombination(BaseModelStrict):
    combination_id: str
    parameters: list[SweepParameterAssignment] = Field(default_factory=list)
    run_hash: str | None = None
    status: SweepCombinationStatus = SweepCombinationStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    trust_gate_summary: SweepTrustGateSummary | None = None

    @model_validator(mode="after")
    def _ensure_terminal_run_hash(self) -> SweepCombination:
        if (
            self.status
            in {
                SweepCombinationStatus.SUCCEEDED,
                SweepCombinationStatus.FAILED,
            }
            and not self.run_hash
        ):
            raise ValueError("run_hash must be set for terminal combination states")
        return self

    @computed_field
    def duration_ms(self) -> int | None:  # pragma: no mutate - computed only
        if self.started_at is None or self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)

    def parameter_map(self) -> dict[str, ParameterValue]:
        return {assignment.name: assignment.value for assignment in self.parameters}


class TickerSweepManifest(BaseModelStrict):
    ticker: str
    combination_cap: int
    cap_status: SweepCapStatus = SweepCapStatus.OK
    data_quality_status: SweepDataQualityStatus = SweepDataQualityStatus.PASS
    variance_metrics: dict[str, float | int] = Field(default_factory=dict)
    manifest_path: str | None = None
    partial_execution_reason: str | None = None


class SweepManifest(BaseModelStrict):
    schema_version: str = Field(default="sweep_manifest.v1")
    sweep_id: str
    status: SweepStatus = SweepStatus.PENDING
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    initiator: str | None = None
    parameter_definitions: list[ParameterDefinition] = Field(default_factory=list)
    combinations: list[SweepCombination] = Field(default_factory=list)
    tickers: list[TickerSweepManifest] = Field(default_factory=list)
    combination_cap: int
    derived_metrics: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    trust_gates: SweepTrustGateEvidence = Field(default_factory=SweepTrustGateEvidence)

    @model_validator(mode="after")
    def _validate_uniqueness(self) -> SweepManifest:
        seen: set[str] = set()
        for combo in self.combinations:
            if combo.combination_id in seen:
                raise ValueError(
                    f"Duplicate combination id detected: {combo.combination_id}"
                )
            seen.add(combo.combination_id)
        return self

    @computed_field
    def aggregates(self) -> dict[str, int | float | None]:
        total = len(self.combinations)
        succeeded = sum(
            1
            for combo in self.combinations
            if combo.status == SweepCombinationStatus.SUCCEEDED
        )
        failed = sum(
            1
            for combo in self.combinations
            if combo.status == SweepCombinationStatus.FAILED
        )
        durations: list[int] = []
        for combo in self.combinations:
            duration_value = cast(int | None, combo.duration_ms)
            if duration_value is not None:
                durations.append(duration_value)
        average_duration = sum(durations) / len(durations) if durations else None
        storage_bytes = self.derived_metrics.get("storage_bytes")
        if isinstance(storage_bytes, (int, float)):
            storage_value: int | float | None
            if isinstance(storage_bytes, float) and storage_bytes.is_integer():
                storage_value = int(storage_bytes)
            else:
                storage_value = storage_bytes
        else:
            storage_value = None
        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "average_duration_ms": average_duration,
            "storage_bytes": storage_value,
        }

    def to_storage_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude_none=False)
        payload["parameter_definitions"] = [
            definition.as_payload() for definition in self.parameter_definitions
        ]
        payload.pop("aggregates", None)
        combinations_payload = payload.get("combinations")
        if isinstance(combinations_payload, list):
            for combo in combinations_payload:
                if isinstance(combo, dict):
                    combo.pop("duration_ms", None)
        return payload

    @classmethod
    def from_storage_dict(cls, payload: Mapping[str, Any]) -> SweepManifest:
        data = dict(payload)
        raw_defs = data.get("parameter_definitions") or []
        parameter_definitions = []
        for entry in raw_defs:
            if not isinstance(entry, Mapping) or "name" not in entry:
                continue
            entry_payload = dict(entry)
            name = str(entry_payload.pop("name"))
            parameter_definitions.append(
                ParameterDefinition.from_payload(name, entry_payload)
            )
        raw_combinations = data.get("combinations") or []
        combinations = [
            SweepCombination.model_validate(entry) for entry in raw_combinations
        ]
        raw_tickers = data.get("tickers") or []
        tickers = [TickerSweepManifest.model_validate(entry) for entry in raw_tickers]
        trust_gates_payload = data.get("trust_gates")
        trust_gates = (
            SweepTrustGateEvidence.model_validate(trust_gates_payload)
            if trust_gates_payload is not None
            else SweepTrustGateEvidence()
        )
        manifest_data = {
            **data,
            "parameter_definitions": parameter_definitions,
            "combinations": combinations,
            "tickers": tickers,
            "trust_gates": trust_gates,
        }
        return cls.model_validate(manifest_data)


__all__ = [
    "ArtifactDescriptor",
    "TrustGateManifest",
    "TrustGateGateDescriptor",
    "RunManifest",
    "compute_composite_hash_from",
    "SweepCombinationStatus",
    "SweepStatus",
    "SweepCapStatus",
    "SweepDataQualityStatus",
    "SweepParameterAssignment",
    "SweepTrustGateSummary",
    "SweepTrustGateCheckpoint",
    "SweepTrustGateEvidence",
    "SweepTrustGateValidationStatus",
    "SweepCombination",
    "TickerSweepManifest",
    "SweepManifest",
]
