"""Microbenchmark harness (T068).

Goals:
- Measure end-to-end run orchestration latency (config -> artifacts) for a small synthetic dataset.
- Provide stable, reproducible timings (single-thread, fixed seed, warm-up + measured loops).
- Output JSON summary so CI can parse in future (optional thresholds).

Usage:
  poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output bench_result.json

Notes:
- Keeps dataset in-memory using a generated candle frame (no IO beyond artifacts output).
- For consistency, artifacts directory is cleaned between iterations unless --keep-artifacts.
"""

from __future__ import annotations

import argparse
import importlib
import json
import statistics
import sys
import time
import uuid
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Ensure project packages are on sys.path when running as standalone script (Poetry normally
# handles this for pytest/CLI invocations, but direct execution may require explicit wiring).
ROOT = Path(__file__).resolve().parents[2]
SRC_CANDIDATES: tuple[Path, ...] = (
    ROOT / "alphaforge-brain",
    ROOT / "alphaforge-brain" / "src",
    ROOT / "src",
)
for candidate in SRC_CANDIDATES:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:  # Ensure structlog PrintLogger exposes .name for structlog.stdlib.add_logger_name
    _structlog_module = importlib.import_module("structlog._loggers")
    _structlog_print_logger = getattr(_structlog_module, "PrintLogger", None)
    if _structlog_print_logger is not None and not hasattr(
        _structlog_print_logger, "name"
    ):
        _structlog_print_logger.name = "structlog"
except ModuleNotFoundError:  # pragma: no cover - structlog internals may change
    pass

try:  # Patch add_logger_name to tolerate loggers without .name
    _structlog_stdlib = importlib.import_module("structlog.stdlib")
    _original_add_logger_name = getattr(_structlog_stdlib, "add_logger_name", None)

    if callable(_original_add_logger_name):

        def _safe_add_logger_name(
            logger: Any, method_name: str, event_dict: dict[str, Any]
        ) -> dict[str, Any]:
            try:
                return _original_add_logger_name(logger, method_name, event_dict)
            except AttributeError:
                name = getattr(logger, "name", None)
                if name is None:
                    underlying = getattr(logger, "_logger", None)
                    name = getattr(underlying, "name", None)
                event_dict["logger"] = name or "structlog"
                return event_dict

        _structlog_stdlib.add_logger_name = _safe_add_logger_name
except ModuleNotFoundError:  # pragma: no cover - structlog internals may change
    pass

from domain.run.create import InMemoryRunRegistry, create_or_get  # noqa: E402
from domain.schemas.run_config import (  # noqa: E402
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

from infra.db import get_connection  # noqa: E402

try:
    from services.trust_gates.suite_service import (
        DEFAULT_GATE_ORDER as _DEFAULT_TRUST_GATE_ORDER,
    )

    TRUST_GATE_ORDER: tuple[str, ...] = tuple(_DEFAULT_TRUST_GATE_ORDER)
except (
    Exception
):  # pragma: no cover - benchmark should not fail if module layout shifts
    TRUST_GATE_ORDER = (
        "golden_run",
        "causality",
        "ingest_idempotency",
        "timezone",
        "universe_stamp",
        "equity_reconciliation",
        "accounting",
    )

DEFAULT_BASELINE_PATH = ROOT / "artifacts" / "perf_baseline.json"
STAGE_ORDER: tuple[str, ...] = (
    "total",
    "permutation",
    "cross_validation",
    "bias_adjustment",
    "execution_realism",
    "aggregate",
)
STAGE_RATIO_LIMITS: dict[str, float] = {
    "permutation": 0.7,
    "cross_validation": 0.6,
    "bias_adjustment": 0.5,
    "execution_realism": 0.5,
    "aggregate": 0.3,
}


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value)
        return None
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"true", "1", "yes", "on"}:
            return True
        if lower in {"false", "0", "no", "off"}:
            return False
    return None


def _normalise_metric_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_normalise_metric_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _normalise_metric_value(v) for k, v in value.items()}
    return str(value)


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    data = list(values)
    if not data:
        return None
    if len(data) == 1:
        return data[0]
    try:
        quantiles = statistics.quantiles(data, n=100, method="inclusive")
    except ValueError:  # pragma: no cover - defensive guard for extreme edge cases
        data.sort()
        return data[-1]
    index = max(0, min(len(quantiles) - 1, int(percentile * 100) - 1))
    return quantiles[index]


def fetch_validation_spans(run_hash: str) -> dict[str, dict[str, Any]]:
    spans: dict[str, dict[str, Any]] = {}
    query = """
        SELECT phase, duration_ms, extra_json
        FROM phase_metrics
        WHERE run_hash = ? AND phase LIKE 'validation.%'
    """
    with get_connection() as conn:
        for row in conn.execute(query, (run_hash,)):
            phase = row["phase"]
            if not isinstance(phase, str):
                continue
            stage = phase.split(".", 1)[1] if "." in phase else phase
            metrics: dict[str, Any] = {}
            duration_value = row["duration_ms"]
            if duration_value is not None:
                metrics["duration_ms"] = float(duration_value)

            extra_json = row["extra_json"]
            if isinstance(extra_json, str) and extra_json:
                try:
                    extra = json.loads(extra_json)
                except json.JSONDecodeError:  # pragma: no cover - defensive guard
                    extra = {}
                if isinstance(extra, dict):
                    attributes = extra.get("attributes")
                    if isinstance(attributes, dict):
                        for key, value in attributes.items():
                            if key == "duration_ms":
                                continue
                            metrics[key] = _normalise_metric_value(value)
                    for key, value in extra.items():
                        if key == "attributes":
                            continue
                        metrics[key] = _normalise_metric_value(value)
            spans[stage] = metrics
    return spans


def load_baseline_mean_ms(path: Path) -> float | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:  # pragma: no cover - baseline corruption guard
        return None
    summary = data.get("summary")
    if isinstance(summary, dict):
        mean_ms = summary.get("mean_ms")
        if isinstance(mean_ms, (int, float)):
            return float(mean_ms)
    return None


def summarize_validation(
    iteration_details: list[dict[str, Any]],
) -> OrderedDict[str, dict[str, Any]]:
    stage_durations: dict[str, list[float]] = defaultdict(list)
    stage_cpu: dict[str, list[float]] = defaultdict(list)
    stage_mem_delta_mb: dict[str, list[float]] = defaultdict(list)
    stage_mem_peak_mb: dict[str, list[float]] = defaultdict(list)
    stage_enabled_counts: dict[str, int] = defaultdict(int)
    stage_disabled_counts: dict[str, int] = defaultdict(int)

    for detail in iteration_details:
        spans = detail.get("validation", {})
        if not isinstance(spans, dict):
            continue
        for stage, metrics in spans.items():
            if not isinstance(metrics, dict):
                continue
            duration_ms = _coerce_float(metrics.get("duration_ms"))
            if duration_ms is not None:
                stage_durations[stage].append(duration_ms)

            cpu_ms = _coerce_float(metrics.get("cpu_ms"))
            if cpu_ms is not None:
                stage_cpu[stage].append(cpu_ms)

            mem_delta = _coerce_float(metrics.get("mem_delta_bytes"))
            if mem_delta is not None:
                stage_mem_delta_mb[stage].append(mem_delta / (1024 * 1024))

            mem_peak = _coerce_float(metrics.get("mem_peak_delta_bytes"))
            if mem_peak is not None:
                stage_mem_peak_mb[stage].append(mem_peak / (1024 * 1024))

            enabled_val = _coerce_bool(metrics.get("enabled"))
            if enabled_val is True:
                stage_enabled_counts[stage] += 1
            elif enabled_val is False:
                stage_disabled_counts[stage] += 1

    ordered: OrderedDict[str, dict[str, Any]] = OrderedDict()
    total_durations = stage_durations.get("total", [])
    total_mean = statistics.mean(total_durations) if total_durations else None

    def _rounded(value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 4)

    for stage in STAGE_ORDER:
        durations = stage_durations.get(stage)
        if not durations:
            continue
        stats: dict[str, Any] = {
            "count": len(durations),
            "mean_ms": _rounded(statistics.mean(durations)),
            "median_ms": _rounded(statistics.median(durations)),
            "p95_ms": _rounded(_percentile(durations, 0.95)),
            "max_ms": _rounded(max(durations)),
        }
        if total_mean and total_mean > 0:
            stats["ratio_vs_total"] = _rounded(stats["mean_ms"] / total_mean)  # type: ignore[arg-type]
        if stage_cpu.get(stage):
            stats["cpu_mean_ms"] = _rounded(statistics.mean(stage_cpu[stage]))
            stats["cpu_max_ms"] = _rounded(max(stage_cpu[stage]))
        if stage_mem_delta_mb.get(stage):
            stats["mem_delta_max_mb"] = _rounded(max(stage_mem_delta_mb[stage]))
        if stage_mem_peak_mb.get(stage):
            stats["mem_peak_delta_max_mb"] = _rounded(max(stage_mem_peak_mb[stage]))
        enabled_total = stage_enabled_counts.get(stage, 0) + stage_disabled_counts.get(
            stage, 0
        )
        if enabled_total:
            stats["enabled_fraction"] = _rounded(
                stage_enabled_counts.get(stage, 0) / enabled_total
            )
        ordered[stage] = stats

    # Include any additional stages (unexpected) to aid debugging
    for stage, durations in sorted(stage_durations.items()):
        if stage in ordered:
            continue
        stats: dict[str, Any] = {
            "count": len(durations),
            "mean_ms": _rounded(statistics.mean(durations)),
            "median_ms": _rounded(statistics.median(durations)),
            "p95_ms": _rounded(_percentile(durations, 0.95)),
            "max_ms": _rounded(max(durations)),
        }
        if total_mean and total_mean > 0:
            stats["ratio_vs_total"] = _rounded(stats["mean_ms"] / total_mean)  # type: ignore[arg-type]
        ordered[stage] = stats

    return ordered


def _extract_trust_gate_summary(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    summary: dict[str, Any] = {}
    status = raw.get("status")
    if isinstance(status, str):
        summary["status"] = status

    runtime_ms = _coerce_float(raw.get("runtime_ms"))
    if runtime_ms is not None:
        summary["runtime_ms"] = runtime_ms

    for key in (
        "suite_id",
        "suite_version",
        "tolerance_profile",
        "config_hash",
        "executed_at",
        "signature_path",
        "report_path",
    ):
        value = raw.get(key)
        if value is not None:
            summary[key] = value

    enabled_gates = raw.get("enabled_gates")
    if isinstance(enabled_gates, list):
        summary["enabled_gates"] = [
            gate for gate in enabled_gates if isinstance(gate, str)
        ]

    gates_payload: list[dict[str, Any]] = []
    for gate in raw.get("gates", []):
        if not isinstance(gate, dict):
            continue
        name = gate.get("name")
        if not isinstance(name, str):
            continue
        gate_entry: dict[str, Any] = {"name": name}
        gate_status = gate.get("status")
        if isinstance(gate_status, str):
            gate_entry["status"] = gate_status
        duration = _coerce_float(gate.get("duration_ms"))
        if duration is not None:
            gate_entry["duration_ms"] = duration
        for attr in ("artifact", "correlation_id", "waiver_ref"):
            value = gate.get(attr)
            if isinstance(value, str):
                gate_entry[attr] = value
        metrics = gate.get("metrics")
        if isinstance(metrics, dict):
            gate_entry["metrics"] = {
                str(k): _normalise_metric_value(v) for k, v in metrics.items()
            }
        diagnostics = gate.get("diagnostics")
        if isinstance(diagnostics, dict):
            gate_entry["diagnostics"] = {
                str(k): _normalise_metric_value(v) for k, v in diagnostics.items()
            }
        gates_payload.append(gate_entry)

    summary["gates"] = gates_payload
    return summary


def summarize_trust_gates(
    iteration_details: list[dict[str, Any]],
) -> dict[str, Any]:
    stage_durations: dict[str, list[float]] = defaultdict(list)
    stage_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stage_waived_counts: dict[str, int] = defaultdict(int)
    stage_run_counts: dict[str, int] = defaultdict(int)
    suite_status_counts: Counter[str] = Counter()
    enabled_counts: Counter[str] = Counter()

    total_stage_key = "trust_suite.total"

    for detail in iteration_details:
        trust_gate = detail.get("trust_gate")
        if not isinstance(trust_gate, dict):
            continue

        stage_run_counts[total_stage_key] += 1
        suite_status = trust_gate.get("status")
        if isinstance(suite_status, str):
            suite_status_counts[suite_status] += 1
            stage_status_counts[total_stage_key][suite_status] += 1

        runtime_ms = _coerce_float(trust_gate.get("runtime_ms"))
        if runtime_ms is not None:
            stage_durations[total_stage_key].append(runtime_ms)

        enabled = trust_gate.get("enabled_gates")
        if isinstance(enabled, list):
            for gate_name in enabled:
                if isinstance(gate_name, str):
                    enabled_counts[gate_name] += 1

        for gate in trust_gate.get("gates", []):
            if not isinstance(gate, dict):
                continue
            gate_name = gate.get("name")
            if not isinstance(gate_name, str):
                continue
            stage_key = f"trust_suite.{gate_name}"
            stage_run_counts[stage_key] += 1
            gate_status = gate.get("status")
            if isinstance(gate_status, str):
                stage_status_counts[stage_key][gate_status] += 1
            duration = _coerce_float(gate.get("duration_ms"))
            if duration is not None:
                stage_durations[stage_key].append(duration)
            waiver = gate.get("waiver_ref")
            if isinstance(waiver, str):
                stage_waived_counts[stage_key] += 1

    def _rounded(value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 4)

    total_mean = (
        statistics.mean(stage_durations[total_stage_key])
        if stage_durations.get(total_stage_key)
        else None
    )

    ordered: OrderedDict[str, dict[str, Any]] = OrderedDict()
    stage_sequence = [total_stage_key] + [
        f"trust_suite.{gate}" for gate in TRUST_GATE_ORDER
    ]

    for stage_key in stage_sequence:
        durations = stage_durations.get(stage_key, [])
        run_count = stage_run_counts.get(stage_key, 0)
        status_counts = stage_status_counts.get(stage_key)
        waived_runs = stage_waived_counts.get(stage_key, 0)

        if not durations and run_count == 0 and not status_counts:
            continue

        stats: dict[str, Any] = {
            "runs_observed": run_count,
            "count": len(durations),
        }
        if durations:
            stats.update(
                {
                    "mean_ms": _rounded(statistics.mean(durations)),
                    "median_ms": _rounded(statistics.median(durations)),
                    "p95_ms": _rounded(_percentile(durations, 0.95)),
                    "max_ms": _rounded(max(durations)),
                }
            )
            if stage_key != total_stage_key and total_mean and total_mean > 0:
                stats["ratio_vs_suite_total"] = _rounded(
                    stats["mean_ms"] / total_mean  # type: ignore[arg-type]
                )
            elif stage_key == total_stage_key:
                stats["ratio_vs_suite_total"] = 1.0

        if status_counts:
            stats["status_counts"] = dict(sorted(status_counts.items()))
        if stage_key != total_stage_key and run_count:
            if waived_runs:
                stats["waived_runs"] = waived_runs
                stats["waived_fraction"] = _rounded(waived_runs / run_count)

        ordered[stage_key] = stats

    return {
        "stages": ordered,
        "suite_status_counts": dict(sorted(suite_status_counts.items())),
        "enabled_counts": dict(sorted(enabled_counts.items())),
    }


def compute_sla(
    stage_stats: dict[str, dict[str, Any]],
    baseline_mean_ms: float | None,
) -> dict[str, Any]:
    if not stage_stats:
        return {
            "baseline_mean_ms": baseline_mean_ms,
            "limit_ms": None,
            "total_mean_ms": None,
            "ratio_limits": STAGE_RATIO_LIMITS,
            "passes": True,
            "violations": [],
            "note": "Validation modules disabled; no spans collected.",
        }

    total_stats = stage_stats.get("total", {})
    total_mean_ms = total_stats.get("mean_ms")
    violations: list[str] = []
    passes = True

    limit_ms: float | None = None
    if baseline_mean_ms is not None and isinstance(total_mean_ms, (int, float)):
        limit_ms = round(baseline_mean_ms * 1.2, 4)
        if total_mean_ms > limit_ms:
            passes = False
            violations.append(
                f"validation.total mean {total_mean_ms:.3f}ms exceeds SLA limit {limit_ms:.3f}ms"
            )

    if isinstance(total_mean_ms, (int, float)) and total_mean_ms > 0:
        for stage, ratio_limit in STAGE_RATIO_LIMITS.items():
            stats = stage_stats.get(stage)
            if not stats:
                continue
            ratio = stats.get("ratio_vs_total")
            if isinstance(ratio, (int, float)) and ratio > ratio_limit:
                passes = False
                violations.append(
                    f"{stage} mean share {ratio:.2f} exceeds ratio limit {ratio_limit:.2f}"
                )

    summary: dict[str, Any] = {
        "baseline_mean_ms": baseline_mean_ms,
        "limit_ms": limit_ms,
        "total_mean_ms": total_mean_ms,
        "ratio_limits": STAGE_RATIO_LIMITS,
        "passes": passes,
    }
    if violations:
        summary["violations"] = violations
    if baseline_mean_ms is None:
        summary["note"] = "Baseline file not found; limit check skipped."
    return summary


def build_perf_sla_record(
    trust_gates_summary: dict[str, Any],
    baseline_mean_ms: float | None,
    limit_multiplier: float,
    run_hashes: Iterable[str],
) -> dict[str, Any]:
    stages = trust_gates_summary.get("stages", {})
    stage = {}
    if isinstance(stages, dict):
        stage = stages.get("trust_suite.total", {}) or {}

    mean_ms = stage.get("mean_ms") if isinstance(stage, dict) else None
    p95_ms = stage.get("p95_ms") if isinstance(stage, dict) else None

    mean_value = float(mean_ms) if isinstance(mean_ms, (int, float)) else None
    p95_value = float(p95_ms) if isinstance(p95_ms, (int, float)) else None
    baseline_value = (
        float(baseline_mean_ms) if isinstance(baseline_mean_ms, (int, float)) else None
    )

    passes = False
    if mean_value is not None and baseline_value is not None:
        passes = mean_value <= baseline_value * limit_multiplier

    run_id = None
    for candidate in run_hashes:
        if isinstance(candidate, str) and candidate:
            run_id = candidate
            break
    if run_id is None:
        run_id = f"bench-{uuid.uuid4()}"

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "suite": "trust_gates",
        "mean_ms": mean_value,
        "p95_ms": p95_value,
        "baseline_mean_ms": baseline_value,
        "limit_multiplier": limit_multiplier,
        "pass": passes,
        "run_id": run_id,
        "generated_at": generated_at,
    }


def build_config(seed: int) -> RunConfig:
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
        strategy=StrategySpec(name="dual_sma", params={}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(slippage_bps=5, fee_bps=0.0),
        validation=ValidationSpec(),
        seed=seed,
    )


def run_once(registry: InMemoryRunRegistry, cfg: RunConfig) -> dict[str, Any]:
    start = time.perf_counter()
    run_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
    elapsed = time.perf_counter() - start
    summary = record.get("summary", {})
    validation_spans = fetch_validation_spans(run_hash)
    trust_gate_summary = _extract_trust_gate_summary(
        record.get("trust_gate_summary") if isinstance(record, dict) else None
    )
    return {
        "run_hash": run_hash,
        "created": created,
        "elapsed_sec": elapsed,
        "trade_count": summary.get("trade_count"),
        "validation": validation_spans,
        "trust_gate": trust_gate_summary,
    }


def remove_artifacts(run_hash: str) -> None:
    path = Path("artifacts") / run_hash
    if path.exists():
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    p.unlink()
            except Exception:
                pass
        try:
            path.rmdir()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument(
        "--baseline",
        type=str,
        default=str(DEFAULT_BASELINE_PATH),
        help="Path to JSON baseline with summary.mean_ms for SLA comparison",
    )
    parser.add_argument(
        "--limit-multiplier",
        type=float,
        default=1.5,
        help="Multiplier applied to baseline mean when evaluating trust gate SLA",
    )
    args = parser.parse_args()

    registry = InMemoryRunRegistry()

    warm_cfg = build_config(seed=123)
    for _ in range(args.warmup):
        res = run_once(registry, warm_cfg)
        if not args.keep_artifacts:
            remove_artifacts(res["run_hash"])  # cleanup warmup

    times: list[float] = []
    trade_counts: list[int] = []
    hashes: list[str] = []
    iteration_details: list[dict[str, Any]] = []

    for i in range(args.iterations):
        cfg = build_config(seed=1000 + i)
        res = run_once(registry, cfg)
        times.append(res["elapsed_sec"])
        trade_counts.append(res.get("trade_count") or 0)
        hashes.append(res["run_hash"])
        iteration_details.append(res)
        if not args.keep_artifacts:
            remove_artifacts(res["run_hash"])  # avoid disk skew

    summary = {
        "iterations": args.iterations,
        "warmup": args.warmup,
        "mean_sec": statistics.mean(times) if times else 0.0,
        "median_sec": statistics.median(times) if times else 0.0,
        "p95_sec": (
            statistics.quantiles(times, n=100)[94]
            if len(times) >= 20
            else max(times) if times else 0.0
        ),
        "min_sec": min(times) if times else 0.0,
        "max_sec": max(times) if times else 0.0,
        "trade_count_mean": statistics.mean(trade_counts) if trade_counts else 0.0,
        "hash_sample": hashes[:3],
    }

    stage_stats = summarize_validation(iteration_details)
    trust_gates_summary = summarize_trust_gates(iteration_details)
    baseline_mean_ms = load_baseline_mean_ms(Path(args.baseline))
    sla_summary = compute_sla(stage_stats, baseline_mean_ms)
    total_stats = stage_stats.get("total", {})
    if isinstance(total_stats, dict):
        summary["validation_total_mean_ms"] = total_stats.get("mean_ms")
    summary["validation_sla_pass"] = sla_summary.get("passes", True)

    trust_suite_total = trust_gates_summary.get("stages", {}).get("trust_suite.total")
    if isinstance(trust_suite_total, dict):
        summary["trust_gate_total_mean_ms"] = trust_suite_total.get("mean_ms")

    perf_sla_record = build_perf_sla_record(
        trust_gates_summary,
        baseline_mean_ms,
        args.limit_multiplier,
        hashes,
    )

    summary["trust_gate_sla_pass"] = perf_sla_record["pass"]

    payload = {
        "runs": summary,
        "raw_times": times,
        "iterations": iteration_details,
        "validation": {
            "stages": stage_stats,
            "sla": sla_summary,
        },
        "trust_gates": trust_gates_summary,
        "perf_sla": perf_sla_record,
    }

    print(json.dumps(payload, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
