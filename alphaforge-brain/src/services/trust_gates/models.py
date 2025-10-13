"""Data models for trust gate execution results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence
from uuid import uuid4


@dataclass(frozen=True)
class TrustGateResult:
    """Outcome of a single trust gate evaluation."""

    name: str
    status: str
    metrics: Mapping[str, object] = field(default_factory=dict)
    diagnostics: Mapping[str, object] = field(default_factory=dict)
    tolerance: Mapping[str, object] = field(default_factory=dict)
    artifact: str | None = None
    correlation_id: str | None = None
    duration_ms: int | None = None
    waiver_ref: str | None = None

    @property
    def is_failure(self) -> bool:
        """Return ``True`` when the gate failed or returned a warning state."""

        return self.status in {"fail", "warn"}


@dataclass(frozen=True)
class TrustGateSummary:
    """Aggregated suite output across all trust gates."""

    status: str
    results: list[TrustGateResult]
    runtime_ms: int | None = None
    tolerance_profile: str | None = None
    report_path: str | None = None
    suite_id: str = field(default_factory=lambda: f"tg_suite_{uuid4().hex[:12]}")
    suite_version: int = 1
    config_hash: str | None = None
    enabled_gates: Sequence[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature_path: str | None = None
    schema_version: str = "trust_gates.v1"
    tolerance_profile_version: str | None = None
    tolerance_profile_hash: str | None = None

    def failing_gates(self) -> Iterable[TrustGateResult]:
        """Iterate over gates that did not return a passing status."""

        return (result for result in self.results if result.is_failure)

    def as_dict(self) -> dict[str, object]:
        """Render the summary with full diagnostic payload for CLI / reporting."""

        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "runtime_ms": self.runtime_ms,
            "tolerance_profile": self.tolerance_profile,
            "report_path": self.report_path,
            "signature_path": self.signature_path,
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "config_hash": self.config_hash,
            "executed_at": self.executed_at.isoformat().replace("+00:00", "Z"),
            "enabled_gates": list(self.enabled_gates),
            "tolerance_profile_version": self.tolerance_profile_version,
            "tolerance_profile_hash": self.tolerance_profile_hash,
            "gates": [
                {
                    "name": result.name,
                    "status": result.status,
                    "metrics": dict(result.metrics),
                    "diagnostics": dict(result.diagnostics),
                    "tolerance": dict(result.tolerance),
                    "artifact": result.artifact,
                    "correlation_id": result.correlation_id,
                    "duration_ms": result.duration_ms,
                    "waiver_ref": result.waiver_ref,
                }
                for result in self.results
            ],
        }

    def manifest_block(self) -> dict[str, object]:
        """Return manifest-friendly representation with minimal payload."""
        manifest_results: list[dict[str, object]] = []
        for result in self.results:
            entry: dict[str, object] = {
                "name": result.name,
                "status": result.status,
            }
            if result.artifact:
                entry["artifact"] = result.artifact
            if result.correlation_id:
                entry["correlation_id"] = result.correlation_id
            if result.waiver_ref:
                entry["waiver_ref"] = result.waiver_ref
            if result.duration_ms is not None:
                entry["duration_ms"] = result.duration_ms
            if result.tolerance:
                entry["tolerance"] = dict(result.tolerance)
            manifest_results.append(entry)

        block: dict[str, object] = {
            "schema_version": self.schema_version,
            "status": self.status,
            "suite_id": self.suite_id,
            "executed_at": self.executed_at.isoformat().replace("+00:00", "Z"),
            "suite_version": self.suite_version,
            "config_hash": self.config_hash,
            "tolerance_profile": self.tolerance_profile,
            "tolerance_profile_version": self.tolerance_profile_version,
            "tolerance_profile_hash": self.tolerance_profile_hash,
            "runtime_ms": self.runtime_ms,
            "gates": manifest_results,
        }
        if self.signature_path:
            block["signature_path"] = self.signature_path
        if self.report_path:
            block["report_path"] = self.report_path
        if self.enabled_gates:
            block["enabled_gates"] = list(self.enabled_gates)
        return block
