from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from .models import (
    BottleneckConfidence,
    BottleneckEntry,
    OwnerAssignment,
    ValidationPerformanceReport,
)

__all__ = ["build_validation_report", "BottleneckSnapshot"]


@dataclass(frozen=True)
class BottleneckSnapshot:
    metric: str
    current_mean_ms: float
    baseline_mean_ms: float
    delta_pct: float
    confidence: BottleneckConfidence

    def to_entry(self) -> BottleneckEntry:
        return BottleneckEntry(
            metric=self.metric,
            current_mean_ms=self.current_mean_ms,
            baseline_mean_ms=self.baseline_mean_ms,
            delta_pct=self.delta_pct,
            confidence=self.confidence,
        )


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _resolve_baseline_mean(
    stage: str,
    stats: Mapping[str, Any],
    baseline_summary: Mapping[str, float] | None,
) -> float:
    if baseline_summary and stage in baseline_summary:
        return float(baseline_summary[stage])
    fallback = _coerce_float(stats.get("baseline_mean_ms"))
    if fallback is not None:
        return fallback
    current_mean = _coerce_float(stats.get("mean_ms"))
    if current_mean is None:
        raise ValueError(f"Missing mean_ms for stage '{stage}' in validation summary")
    return current_mean


def _compute_confidence(delta_pct: float) -> BottleneckConfidence:
    if delta_pct >= 40.0:
        return BottleneckConfidence.HIGH
    if delta_pct >= 20.0:
        return BottleneckConfidence.MEDIUM
    return BottleneckConfidence.LOW


def _snapshot_bottlenecks(
    validation_summary: Mapping[str, Mapping[str, Any]],
    baseline_summary: Mapping[str, float] | None,
) -> list[BottleneckSnapshot]:
    snapshots: list[BottleneckSnapshot] = []
    ordered = OrderedDict(validation_summary)
    for stage, stats in ordered.items():
        if stage == "total":
            continue
        current_mean = _coerce_float(stats.get("mean_ms"))
        if current_mean is None:
            continue
        baseline_mean = _resolve_baseline_mean(stage, stats, baseline_summary)
        if baseline_mean <= 0:
            delta_pct = 0.0
        else:
            delta_pct = ((current_mean - baseline_mean) / baseline_mean) * 100.0
        if delta_pct <= 0:
            continue
        snapshot = BottleneckSnapshot(
            metric=stage,
            current_mean_ms=current_mean,
            baseline_mean_ms=baseline_mean,
            delta_pct=round(delta_pct, 4),
            confidence=_compute_confidence(delta_pct),
        )
        snapshots.append(snapshot)
    snapshots.sort(key=lambda item: item.delta_pct, reverse=True)
    return snapshots


def build_validation_report(
    *,
    run_identifier: str | None,
    generated_at: datetime | None,
    baseline_source: Path,
    validation_summary: Mapping[str, Mapping[str, Any]],
    baseline_summary: Mapping[str, float] | None = None,
    owner_assignments: Sequence[OwnerAssignment] | None = None,
    recommendations: Sequence[str] | None = None,
) -> ValidationPerformanceReport:
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    snapshots = _snapshot_bottlenecks(validation_summary, baseline_summary)
    if len(snapshots) < 3:
        raise ValueError(
            "Validation summary must contain at least three measurable stages"
        )

    entries = [snapshot.to_entry() for snapshot in snapshots]

    if run_identifier:
        try:
            report_id = uuid5(NAMESPACE_URL, str(run_identifier))
        except Exception:  # pragma: no cover - fallback for invalid identifiers
            report_id = uuid4()
    else:
        report_id = uuid4()

    report = ValidationPerformanceReport(
        report_id=report_id,
        generated_at=generated_at,
        baseline_source=str(baseline_source),
        bottlenecks=entries,
        owner_assignments=list(owner_assignments or []),
        recommendations=list(recommendations or []),
    )
    return report
