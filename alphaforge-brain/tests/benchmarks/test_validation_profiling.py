from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from services.governance.models import BottleneckConfidence, OwnerAssignment

# Target under test will be implemented in T009
from services.governance.profiling import build_validation_report  # type: ignore


@pytest.mark.unit
def test_build_validation_report_ranks_top_three_bottlenecks_descending() -> None:
    validation_summary = OrderedDict(
        [
            (
                "total",
                {
                    "mean_ms": 1400.0,
                    "median_ms": 1300.0,
                    "p95_ms": 1750.0,
                },
            ),
            (
                "permutation",
                {
                    "mean_ms": 420.0,
                    "median_ms": 400.0,
                    "p95_ms": 600.0,
                },
            ),
            (
                "cross_validation",
                {
                    "mean_ms": 360.0,
                    "median_ms": 355.0,
                    "p95_ms": 500.0,
                },
            ),
            (
                "bias_adjustment",
                {
                    "mean_ms": 280.0,
                    "median_ms": 260.0,
                    "p95_ms": 420.0,
                },
            ),
            (
                "execution_realism",
                {
                    "mean_ms": 220.0,
                    "median_ms": 210.0,
                    "p95_ms": 360.0,
                },
            ),
            (
                "aggregate",
                {
                    "mean_ms": 120.0,
                    "median_ms": 115.0,
                    "p95_ms": 260.0,
                },
            ),
        ]
    )

    baseline_summary = {
        "permutation": 280.0,
        "cross_validation": 300.0,
        "bias_adjustment": 200.0,
        "execution_realism": 150.0,
        "aggregate": 140.0,
    }

    assignments = [
        OwnerAssignment(fr_id="FR-001", owner="alice", due_date=date(2025, 11, 7)),
        OwnerAssignment(fr_id="FR-002", owner="bob", due_date=date(2025, 11, 14)),
    ]

    report = build_validation_report(
        run_identifier="validation-run-123",
        generated_at=datetime(2025, 10, 14, 9, 30, tzinfo=timezone.utc),
        baseline_source=Path("artifacts/perf_baseline.json"),
        validation_summary=validation_summary,
        baseline_summary=baseline_summary,
        owner_assignments=assignments,
        recommendations=["Profile permutation joins", "Enable SIMD kernels"],
    )

    assert len(report.bottlenecks) >= 3
    deltas = [entry.delta_pct for entry in report.bottlenecks]
    assert deltas == sorted(deltas, reverse=True)
    assert all(delta > 0 for delta in deltas[:3])
    assert report.bottlenecks[0].metric == "permutation"
    assert report.bottlenecks[0].confidence in {
        BottleneckConfidence.HIGH,
        BottleneckConfidence.MEDIUM,
        BottleneckConfidence.LOW,
    }
    assert report.owner_assignments == assignments
    assert report.baseline_source.endswith("perf_baseline.json")
