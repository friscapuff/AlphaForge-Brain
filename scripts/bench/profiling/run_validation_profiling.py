from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.governance.models import OwnerAssignment  # noqa: E402
from services.governance.profiling import (  # noqa: E402
    BottleneckSnapshot,
    build_validation_report,
)

try:
    from scripts.bench.perf_run import (  # type: ignore
        STAGE_RATIO_LIMITS,
        load_baseline_mean_ms,
        summarize_validation,
    )
except ModuleNotFoundError:  # pragma: no cover - defensive
    STAGE_RATIO_LIMITS = {}

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

    def summarize_validation(iterations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:  # type: ignore
        raise RuntimeError("summarize_validation unavailable")


def _default_input_path() -> Path:
    return ROOT / "zz_artifacts" / "perf_latest.json"


def _default_output_path() -> Path:
    return ROOT / "zz_artifacts" / "governance" / "validation_report.json"


def _default_alert_log_path() -> Path:
    return ROOT / "zz_artifacts" / "governance" / "validation_bottlenecks.jsonl"


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _parse_owner_entry(value: str) -> OwnerAssignment:
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError(
            f"Owner entry must use format FR-ID:owner:YYYY-MM-DD (got '{value}')"
        )
    fr_id, owner, due_raw = parts
    due_date = date.fromisoformat(due_raw)
    return OwnerAssignment(fr_id=fr_id.strip(), owner=owner.strip(), due_date=due_date)


def _load_owner_assignments(
    path: Path | None, inline: list[str]
) -> list[OwnerAssignment]:
    assignments: list[OwnerAssignment] = []
    if path:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(f"Owner assignment file not found: {path}") from None
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in owner assignment file: {path}") from exc
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                fr_id = item.get("fr_id")
                owner = item.get("owner")
                due = item.get("due_date")
                if not (
                    isinstance(fr_id, str)
                    and isinstance(owner, str)
                    and isinstance(due, str)
                ):
                    continue
                assignments.append(
                    OwnerAssignment(
                        fr_id=fr_id.strip(),
                        owner=owner.strip(),
                        due_date=date.fromisoformat(due),
                    )
                )
    for entry in inline:
        assignments.append(_parse_owner_entry(entry))
    return assignments


def _derive_baseline_stage_means(
    validation_summary: Mapping[str, Mapping[str, Any]],
    baseline_total_ms: float | None,
) -> dict[str, float]:
    stage_baseline: dict[str, float] = {}
    for stage, stats in validation_summary.items():
        if stage == "total":
            continue
        ratio = STAGE_RATIO_LIMITS.get(stage)
        if baseline_total_ms and ratio:
            stage_baseline[stage] = float(baseline_total_ms * ratio)
            continue
        baseline_mean = _coerce_float(stats.get("baseline_mean_ms"))
        if baseline_mean is None:
            current_mean = _coerce_float(stats.get("mean_ms"))
            if current_mean is None:
                raise ValueError(f"Stage '{stage}' missing mean_ms metric")
            baseline_mean = current_mean
        stage_baseline[stage] = baseline_mean
    return stage_baseline


def _persist_bottlenecks(path: Path, snapshots: list[BottleneckSnapshot]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for snapshot in snapshots[:10]:  # log top 10 to avoid noisy files
            payload = {
                "metric": snapshot.metric,
                "current_mean_ms": snapshot.current_mean_ms,
                "baseline_mean_ms": snapshot.baseline_mean_ms,
                "delta_pct": snapshot.delta_pct,
                "confidence": snapshot.confidence.value,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            handle.write(json.dumps(payload))
            handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate validation performance report"
    )
    parser.add_argument("--input", type=Path, default=_default_input_path())
    parser.add_argument(
        "--baseline", type=Path, default=ROOT / "artifacts" / "perf_baseline.json"
    )
    parser.add_argument("--output", type=Path, default=_default_output_path())
    parser.add_argument(
        "--owners",
        type=Path,
        default=None,
        help="Optional JSON file with owner assignments",
    )
    parser.add_argument(
        "--owner",
        action="append",
        default=[],
        help="Inline FR-ID:owner:YYYY-MM-DD assignment (repeatable)",
    )
    parser.add_argument(
        "--recommendation",
        action="append",
        default=[],
        help="Recommendation text to include in the report (repeatable)",
    )
    parser.add_argument(
        "--report-id",
        type=str,
        default=None,
        help="Optional identifier for the profiling run (defaults to hash sample)",
    )
    parser.add_argument(
        "--bottleneck-log",
        type=Path,
        default=_default_alert_log_path(),
        help="Path to append bottleneck snapshots for audit trail",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"input file not found: {args.input}") from None
    except json.JSONDecodeError as exc:  # pragma: no cover - configuration error
        raise SystemExit(f"input file invalid JSON: {args.input}") from exc

    validation_section = payload.get("validation", {})
    validation_summary = validation_section.get("stages")
    if not isinstance(validation_summary, dict):
        iterations = payload.get("iterations")
        if isinstance(iterations, list):
            try:
                validation_summary = summarize_validation(iterations)
            except Exception as exc:  # pragma: no cover - diagnostics aid
                raise SystemExit("unable to summarise validation spans") from exc
    if not isinstance(validation_summary, dict):
        raise SystemExit("validation stages missing from benchmark payload") from None

    baseline_total_ms = load_baseline_mean_ms(args.baseline)
    baseline_summary = _derive_baseline_stage_means(
        validation_summary, baseline_total_ms
    )
    assignments = _load_owner_assignments(args.owners, args.owner)
    generated_at = datetime.now(timezone.utc)
    run_identifier = args.report_id
    if not run_identifier:
        runs_section = payload.get("runs", {})
        if isinstance(runs_section, dict):
            sample = runs_section.get("hash_sample")
            if isinstance(sample, list) and sample:
                if isinstance(sample[0], str):
                    run_identifier = sample[0]
        if not run_identifier:
            run_identifier = generated_at.strftime("validation-%Y%m%d%H%M%S")

    report = build_validation_report(
        run_identifier=run_identifier,
        generated_at=generated_at,
        baseline_source=args.baseline,
        validation_summary=validation_summary,
        baseline_summary=baseline_summary,
        owner_assignments=assignments,
        recommendations=args.recommendation,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    _persist_bottlenecks(
        args.bottleneck_log,
        [
            BottleneckSnapshot(
                metric=entry.metric,
                current_mean_ms=entry.current_mean_ms,
                baseline_mean_ms=entry.baseline_mean_ms,
                delta_pct=entry.delta_pct,
                confidence=entry.confidence,
            )
            for entry in report.bottlenecks
        ],
    )

    print(json.dumps({"status": "ok", "output": str(args.output)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
