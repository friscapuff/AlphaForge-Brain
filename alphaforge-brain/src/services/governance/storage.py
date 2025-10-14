from __future__ import annotations

import json
from pathlib import Path

from .models import BenchmarkTrendAlert, WaiverCadenceSnapshot

__all__ = [
    "governance_artifact_dir",
    "append_benchmark_alert",
    "load_benchmark_alerts",
    "write_waiver_cadence_snapshot",
    "read_waiver_cadence_snapshot",
]

_ALERT_LOG_FILENAME = "benchmark_alerts.jsonl"
_WAIVER_CADENCE_FILENAME = "waiver_cadence.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def governance_artifact_dir(base_dir: Path | None = None) -> Path:
    """Return the governance artifact directory, creating it when missing."""

    directory = (base_dir or (_repo_root() / "zz_artifacts" / "governance")).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def append_benchmark_alert(
    alert: BenchmarkTrendAlert, *, artifact_dir: Path | None = None
) -> Path:
    """Append a benchmark alert entry to the JSONL log."""

    directory = governance_artifact_dir(artifact_dir)
    path = directory / _ALERT_LOG_FILENAME
    serialized = alert.model_dump_json()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.write("\n")
    return path


def load_benchmark_alerts(
    *, artifact_dir: Path | None = None
) -> list[BenchmarkTrendAlert]:
    """Load all benchmark alerts from the JSONL log."""

    directory = governance_artifact_dir(artifact_dir)
    path = directory / _ALERT_LOG_FILENAME
    if not path.exists():
        return []

    alerts: list[BenchmarkTrendAlert] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            alerts.append(BenchmarkTrendAlert.model_validate_json(line))
    return alerts


def write_waiver_cadence_snapshot(
    snapshot: WaiverCadenceSnapshot, *, artifact_dir: Path | None = None
) -> Path:
    """Persist the latest waiver cadence snapshot as formatted JSON."""

    directory = governance_artifact_dir(artifact_dir)
    path = directory / _WAIVER_CADENCE_FILENAME
    payload = snapshot.model_dump(mode="json")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return path


def read_waiver_cadence_snapshot(
    *, artifact_dir: Path | None = None
) -> WaiverCadenceSnapshot | None:
    """Load the waiver cadence snapshot when available."""

    directory = governance_artifact_dir(artifact_dir)
    path = directory / _WAIVER_CADENCE_FILENAME
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return WaiverCadenceSnapshot.model_validate(data)
