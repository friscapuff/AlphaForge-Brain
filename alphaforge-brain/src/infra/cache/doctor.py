"""Diagnostic CLI for cache health and parquet fallbacks."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prometheus_client import CollectorRegistry, Gauge

from ._parquet import load_pyarrow, parquet_available
from .metrics import cache_metrics


@dataclass
class FileInfo:
    path: str
    size: int
    kind: str


@dataclass
class CacheDoctorReport:
    root: str
    parquet_available: bool
    pyarrow_version: str | None
    metrics: dict[str, int]
    generated_at: datetime
    files: list[FileInfo]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "parquet_available": self.parquet_available,
            "pyarrow_version": self.pyarrow_version,
            "generated_at": self.generated_at.isoformat(),
            "metrics": self.metrics,
            "files": [asdict(file) for file in self.files],
        }


@dataclass
class ParquetFallbackAlert:
    path: str
    size_bytes: int
    generated_at: datetime


_fallback_gauge = Gauge(
    "cache_parquet_fallback_active",
    "Number of CSV fallback files detected by cache doctor",
    labelnames=("root",),
)

_registry_gauges: dict[int, Gauge] = {}


def _classify(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            head = f.read(4)
        if head == b"PAR1":
            return "parquet"
    except Exception:
        return "unknown"
    if path.suffix == ".parquet":
        return "csv_fallback"
    if path.suffix == ".csv":
        return "csv_fallback"
    return "unknown"


def _iter_cache_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


def collect_report(root: Path) -> CacheDoctorReport:
    pa_mod = load_pyarrow()
    pa_version = getattr(pa_mod, "__version__", None) if pa_mod else None
    avail = parquet_available()

    files: list[FileInfo] = []
    for path in _iter_cache_files(root):
        try:
            size = path.stat().st_size
        except Exception:
            size = -1
        kind = _classify(path)
        files.append(FileInfo(path=str(path), size=size, kind=kind))

    return CacheDoctorReport(
        root=str(root),
        parquet_available=avail,
        pyarrow_version=pa_version,
        metrics=cache_metrics.get().snapshot(),
        generated_at=datetime.now(timezone.utc),
        files=files,
    )


def emit_parquet_fallback_alerts(
    report: CacheDoctorReport,
    *,
    registry: CollectorRegistry | None = None,
) -> list[ParquetFallbackAlert]:
    fallback_files = [file for file in report.files if file.kind == "csv_fallback"]
    if registry is None:
        gauge = _fallback_gauge
    else:
        key = id(registry)
        existing = _registry_gauges.get(key)
        if existing is None:
            existing = Gauge(
                "cache_parquet_fallback_active",
                "Number of CSV fallback files detected by cache doctor",
                labelnames=("root",),
                registry=registry,
            )
            _registry_gauges[key] = existing
        gauge = existing
    gauge.labels(root=report.root).set(float(len(fallback_files)))

    alerts = [
        ParquetFallbackAlert(
            path=file.path,
            size_bytes=file.size,
            generated_at=report.generated_at,
        )
        for file in fallback_files
    ]
    return alerts


def main() -> int:  # pragma: no cover - CLI thin wrapper
    parser = argparse.ArgumentParser(description="Cache diagnostic tool")
    parser.add_argument(
        "--root", type=Path, default=Path(".cache"), help="Cache root directory"
    )
    parser.add_argument(
        "--alerts",
        type=Path,
        default=None,
        help="Optional JSON Lines file to append fallback alerts to",
    )
    args = parser.parse_args()
    root: Path = args.root

    report = collect_report(root)
    alerts = emit_parquet_fallback_alerts(report)

    if args.alerts:
        args.alerts.parent.mkdir(parents=True, exist_ok=True)
        with args.alerts.open("a", encoding="utf-8") as handle:
            for alert in alerts:
                payload = {
                    "path": alert.path,
                    "size_bytes": alert.size_bytes,
                    "generated_at": alert.generated_at.isoformat(),
                }
                handle.write(json.dumps(payload))
                handle.write("\n")

    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

__all__ = [
    "CacheDoctorReport",
    "FileInfo",
    "ParquetFallbackAlert",
    "collect_report",
    "emit_parquet_fallback_alerts",
    "main",
]
