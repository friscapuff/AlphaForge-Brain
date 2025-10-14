from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.governance.models import (  # noqa: E402
    BenchmarkTrendAlert,
    BenchmarkTrendStatus,
)
from services.governance.storage import append_benchmark_alert  # noqa: E402

try:
    from scripts.bench.perf_run import load_baseline_mean_ms  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - defensive

    def load_baseline_mean_ms(path: Path) -> float | None:  # type: ignore
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        summary = data.get("summary", {})
        mean_ms = summary.get("mean_ms")
        if isinstance(mean_ms, (int, float)):
            return float(mean_ms)
        return None


def _load_latest_mean_ms(path: Path) -> tuple[float | None, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"latest benchmark file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"latest benchmark file invalid JSON: {path}") from exc

    runs = data.get("runs")
    if isinstance(runs, dict):
        value = runs.get("validation_total_mean_ms")
        if isinstance(value, (int, float)):
            return float(value), data

    validation = data.get("validation")
    if isinstance(validation, dict):
        stages = validation.get("stages")
        if isinstance(stages, dict):
            total = stages.get("total")
            if isinstance(total, dict):
                mean_ms = total.get("mean_ms")
                if isinstance(mean_ms, (int, float)):
                    return float(mean_ms), data

    iterations = data.get("iterations")
    if isinstance(iterations, list) and iterations:
        durations: list[float] = []
        for item in iterations:
            if not isinstance(item, dict):
                continue
            validation_span = item.get("validation")
            if not isinstance(validation_span, dict):
                continue
            total = validation_span.get("total")
            if not isinstance(total, dict):
                continue
            duration = total.get("duration_ms")
            if isinstance(duration, (int, float)):
                durations.append(float(duration))
        if durations:
            return sum(durations) / len(durations), data

    return None, data


def _compose_ticket_url(base: str, run_hash: str | None) -> str:
    if run_hash:
        return f"{base.rstrip('/')}/{run_hash}"
    return f"{base.rstrip('/')}/{uuid4()}"


def _latest_run_hash(data: dict[str, Any]) -> str | None:
    runs = data.get("runs")
    if isinstance(runs, dict):
        sample = runs.get("hash_sample")
        if isinstance(sample, list) and sample:
            first = sample[0]
            if isinstance(first, str):
                return first
    iterations = data.get("iterations")
    if isinstance(iterations, list) and iterations:
        element = iterations[0]
        if isinstance(element, dict):
            run_hash = element.get("run_hash")
            if isinstance(run_hash, str):
                return run_hash
    return None


def _post_alert(endpoint: str, alert: BenchmarkTrendAlert) -> None:
    try:
        response = requests.post(
            endpoint,
            json=alert.model_dump(mode="json"),
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover
        raise SystemExit(f"failed to POST alert to governance API: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare benchmark baseline against latest run"
    )
    parser.add_argument(
        "--baseline", type=Path, default=ROOT / "artifacts" / "perf_baseline.json"
    )
    parser.add_argument(
        "--latest", type=Path, default=ROOT / "zz_artifacts" / "perf_latest.json"
    )
    parser.add_argument(
        "--threshold", type=float, default=10.0, help="Alert threshold in percent"
    )
    parser.add_argument(
        "--alert-log",
        type=Path,
        default=ROOT / "zz_artifacts" / "governance" / "benchmark_alert.jsonl",
    )
    parser.add_argument(
        "--ticket-base",
        type=str,
        default="https://alerts.invalid/benchmark",
        help="Base URL used to derive ticket URLs",
    )
    parser.add_argument(
        "--api-endpoint",
        type=str,
        default=None,
        help="Optional governance API endpoint to POST alerts to",
    )
    args = parser.parse_args(argv)

    baseline_ms = load_baseline_mean_ms(args.baseline)
    if baseline_ms is None:
        raise SystemExit(f"baseline file missing mean_ms: {args.baseline}") from None

    latest_ms, data = _load_latest_mean_ms(args.latest)
    if latest_ms is None:
        raise SystemExit("unable to determine latest validation mean")

    delta_pct = (
        ((latest_ms - baseline_ms) / baseline_ms) * 100.0 if baseline_ms else 0.0
    )

    if delta_pct < args.threshold:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "delta_pct": round(delta_pct, 4),
                    "threshold": args.threshold,
                }
            )
        )
        return 0

    run_hash = _latest_run_hash(data)
    ticket_url = _compose_ticket_url(args.ticket_base, run_hash)
    alert = BenchmarkTrendAlert(
        alert_id=uuid4(),
        generated_at=datetime.now(timezone.utc),
        metric_key="validation.total.mean_ms",
        baseline_ms=baseline_ms,
        observed_ms=latest_ms,
        delta_pct=round(delta_pct, 4),
        ticket_url=ticket_url,
        status=BenchmarkTrendStatus.OPEN,
    )

    append_benchmark_alert(alert)
    args.alert_log.parent.mkdir(parents=True, exist_ok=True)
    with args.alert_log.open("a", encoding="utf-8") as handle:
        handle.write(alert.model_dump_json())
        handle.write("\n")

    if args.api_endpoint:
        _post_alert(args.api_endpoint, alert)

    print(
        json.dumps(
            {
                "status": "alert",
                "delta_pct": round(delta_pct, 4),
                "observed_ms": latest_ms,
                "baseline_ms": baseline_ms,
                "ticket_url": ticket_url,
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
