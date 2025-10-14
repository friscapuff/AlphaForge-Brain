from __future__ import annotations

from datetime import datetime, timezone

from prometheus_client import CollectorRegistry

from infra.cache.doctor import (
    CacheDoctorReport,
    FileInfo,
    emit_parquet_fallback_alerts,
)


def test_emit_parquet_fallback_alerts_sets_metric_and_returns_alerts() -> None:
    report = CacheDoctorReport(
        root="cache/candles",
        parquet_available=False,
        pyarrow_version="17.0.0",
        metrics={"hits": 1, "misses": 2, "rebuilds": 0, "writes": 1},
        generated_at=datetime(2025, 10, 14, 10, 0, tzinfo=timezone.utc),
        files=[
            FileInfo(path="cache/candles/data1.parquet", size=128, kind="parquet"),
            FileInfo(
                path="cache/candles/data2.parquet",
                size=256,
                kind="csv_fallback",
            ),
        ],
    )

    registry = CollectorRegistry()
    alerts = emit_parquet_fallback_alerts(report, registry=registry)

    metric_value = registry.get_sample_value(
        "cache_parquet_fallback_active",
        labels={"root": "cache/candles"},
    )
    assert metric_value == 1.0
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.path == "cache/candles/data2.parquet"
    assert alert.size_bytes == 256
    assert alert.generated_at.tzinfo is not None
