from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

from models.base import BaseModelStrict
from pydantic import Field, HttpUrl, PositiveFloat, field_validator, model_validator

__all__ = [
    "BottleneckConfidence",
    "BenchmarkTrendStatus",
    "CapStatus",
    "WaiverEscalationStatus",
    "BottleneckEntry",
    "OwnerAssignment",
    "ValidationPerformanceReport",
    "BenchmarkTrendAlert",
    "ConfigChangeLedger",
    "WaiverCadenceRecord",
    "WaiverCadenceSnapshot",
    "SweepAcceptanceResult",
]

_CANONICAL_BASELINE_SUFFIX = "perf_baseline.json"
_MIN_BENCHMARK_DELTA = 10.0
_MIN_BOTTLENECKS = 3
_ESCALATION_WARNING_THRESHOLD = 45
_ESCALATION_CRITICAL_THRESHOLD = 60


class BottleneckConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BenchmarkTrendStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class CapStatus(str, Enum):
    PASS = "pass"
    HIT = "hit"


class WaiverEscalationStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    ESCALATED = "escalated"


class BottleneckEntry(BaseModelStrict):
    metric: str
    current_mean_ms: PositiveFloat
    baseline_mean_ms: PositiveFloat
    delta_pct: PositiveFloat
    confidence: BottleneckConfidence

    @field_validator("delta_pct")
    @classmethod
    def _ensure_positive_delta(cls, value: float) -> float:
        if value < 0:
            raise ValueError("delta_pct must be non-negative")
        return value


class OwnerAssignment(BaseModelStrict):
    fr_id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    due_date: date


class ValidationPerformanceReport(BaseModelStrict):
    report_id: UUID
    generated_at: datetime
    baseline_source: str
    bottlenecks: list[BottleneckEntry]
    owner_assignments: list[OwnerAssignment]
    recommendations: list[str] = Field(default_factory=list)

    @field_validator("baseline_source")
    @classmethod
    def _validate_baseline_source(cls, value: str) -> str:
        path = Path(value)
        if path.name != _CANONICAL_BASELINE_SUFFIX:
            raise ValueError(
                f"baseline_source must reference canonical manifest '*{_CANONICAL_BASELINE_SUFFIX}', "
                f"received '{value}'"
            )
        return value

    @model_validator(mode="after")
    def _ensure_minimum_bottlenecks(self) -> ValidationPerformanceReport:
        if len(self.bottlenecks) < _MIN_BOTTLENECKS:
            raise ValueError(
                f"ValidationPerformanceReport requires at least {_MIN_BOTTLENECKS} bottleneck entries"
            )
        return self


class BenchmarkTrendAlert(BaseModelStrict):
    alert_id: UUID
    generated_at: datetime
    metric_key: str
    baseline_ms: PositiveFloat
    observed_ms: PositiveFloat
    delta_pct: PositiveFloat
    ticket_url: HttpUrl
    status: BenchmarkTrendStatus

    @field_validator("delta_pct")
    @classmethod
    def _validate_delta(cls, value: float) -> float:
        if value < _MIN_BENCHMARK_DELTA:
            raise ValueError(
                f"BenchmarkTrendAlert requires delta_pct ≥ {_MIN_BENCHMARK_DELTA}, received {value}"
            )
        return value

    @model_validator(mode="after")
    def _validate_ticket_requirements(self) -> BenchmarkTrendAlert:
        if self.status != BenchmarkTrendStatus.OPEN and not self.ticket_url:
            raise ValueError(
                "ticket_url must be provided once an alert is acknowledged or resolved"
            )
        return self


class ConfigChangeLedger(BaseModelStrict):
    entry_id: UUID
    file_path: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    checksum: str = Field(min_length=1)
    signed_by: str = Field(min_length=1)
    signed_at: datetime
    change_log_ref: str = Field(min_length=1)


class WaiverCadenceRecord(BaseModelStrict):
    waiver_id: str = Field(min_length=1)
    fr_ids: list[str] = Field(default_factory=list)
    opened_at: date
    age_days: int = Field(ge=0)
    escalation_status: WaiverEscalationStatus
    next_action: str = Field(default="", repr=False)

    @model_validator(mode="after")
    def _enforce_escalation_policy(self) -> WaiverCadenceRecord:
        if self.age_days >= _ESCALATION_CRITICAL_THRESHOLD:
            required = WaiverEscalationStatus.ESCALATED
        elif self.age_days >= _ESCALATION_WARNING_THRESHOLD:
            required = WaiverEscalationStatus.WARNING
        else:
            required = WaiverEscalationStatus.NORMAL

        if self.escalation_status != required:
            raise ValueError(
                "Escalation status mismatch: age_days="
                f"{self.age_days} requires {required.value}, received {self.escalation_status.value}"
            )
        return self


class WaiverCadenceSnapshot(BaseModelStrict):
    generated_at: datetime
    items: list[WaiverCadenceRecord] = Field(default_factory=list)


class SweepAcceptanceResult(BaseModelStrict):
    scenario_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    input_payload_hash: str = Field(min_length=1)
    expected_ordering: list[str] = Field(default_factory=list)
    observed_ordering: list[str] = Field(default_factory=list)
    cap_status: CapStatus
    anomaly_flags: list[str] = Field(default_factory=list)
    runbook_link: HttpUrl

    @model_validator(mode="after")
    def _validate_determinism(self) -> SweepAcceptanceResult:
        if (
            self.expected_ordering
            and self.observed_ordering
            and (len(self.expected_ordering) != len(self.observed_ordering))
        ):
            raise ValueError(
                "Expected and observed ordering must be comparable sequences"
            )
        return self
