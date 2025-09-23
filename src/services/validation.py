"""Data anomaly detection utilities (T045).

Detects gaps, duplicates, and basic calendar anomalies on a sequence of
timestamp integers (e.g., epoch ms) or datetime objects.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime


class AnomalyReport(dict[str, int]):
    """Structured anomaly counters.

    Keys:
        gap_count: number of detected temporal gaps (threshold heuristic)
        duplicate_count: number of duplicate timestamps
        holiday_gap_count: placeholder for calendar-aware gap classification (future)
    """
    # Inherits from dict for simple JSON serialization; explicit type param for mypy.
    ...


def detect_anomalies(timestamps: Iterable[datetime]) -> AnomalyReport:
    ordered: list[datetime] = sorted(timestamps)
    report: AnomalyReport = AnomalyReport(gap_count=0, duplicate_count=0, holiday_gap_count=0)
    if not ordered:
        return report
    seen: set[datetime] = set()
    prev: datetime | None = None
    for ts in ordered:
        if ts in seen:
            report["duplicate_count"] += 1
        seen.add(ts)
        if prev is not None:
            delta = (ts - prev).total_seconds()
            # if gap > typical 60s assume missing bars (placeholder threshold)
            if delta > 60:
                report["gap_count"] += 1
        prev = ts
    return report

__all__ = ["AnomalyReport", "detect_anomalies"]
