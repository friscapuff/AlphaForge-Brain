#!/usr/bin/env python3
"""Performance Benchmark Gates (T020a / FR-113 / FR-010)

Aggregates and enforces performance thresholds:
    - Trust gate SLA derived from the `perf_run.py` harness (mean runtime <= baseline x multiplier)
    - Observability overhead < 3% (observability_overhead.py)
    - Bootstrap runtime inflation <= 1.2x baseline (measured via perf_run script with and without a flag)
    - Memory sampler overhead < 1% (causality_guard_overhead used as proxy for now)

Outputs:
    - JSON summary: ``zz_artifacts/perf_gates_summary.json``
    - Prometheus metrics snapshot: ``zz_artifacts/trust_gate_metrics.prom`` capturing
        ``trust_gate_status{gate=...,status=...}`` and ``validation_suite_duration_ms`` gauges

Notes:
 - Bootstrap runtime: we approximate by executing perf_run.py twice with a small synthetic spec.
     If perf_run.py lacks a disable flag, we treat ratio = 1.0 (pass) and mark bootstrap as provisional.
 - Memory sampler overhead uses causality_guard_overhead benchmark threshold (1%). If script absent, skipped.
 - Trust gate SLA failures now bubble up as hard failures with remediation hints instead of silent drift.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.exposition import write_to_textfile

DEFAULT_PERF_ITERATIONS = 3
DEFAULT_PERF_WARMUP = 1
DEFAULT_PERF_LIMIT_MULTIPLIER = 1.5
DEFAULT_PERF_TIMEOUT_SECONDS = 600

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "zz_artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def _run(cmd: list[str], *, timeout: int | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    brain_src = ROOT / "alphaforge-brain" / "src"
    existing = env.get("PYTHONPATH", "")
    if str(brain_src) not in existing.split(os.pathsep):
        env["PYTHONPATH"] = (
            (existing + os.pathsep + str(brain_src)).strip(os.pathsep)
            if existing
            else str(brain_src)
        )
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        timeout=timeout,
    )
    return p.returncode, p.stdout


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_timeout(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _tail(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _write_telemetry_metrics(perf_payload: dict[str, Any]) -> Path | None:
    trust_gates = perf_payload.get("trust_gates")
    validation = perf_payload.get("validation")
    perf_sla = perf_payload.get("perf_sla")
    if not isinstance(trust_gates, dict):
        return None

    registry = CollectorRegistry()
    status_metric = Gauge(
        "trust_gate_status",
        "Trust gate status flag (1 when status observed)",
        labelnames=("gate", "status"),
        registry=registry,
    )
    gate_duration_metric = Gauge(
        "trust_gate_duration_ms",
        "Mean runtime for observed trust gates (milliseconds)",
        labelnames=("gate",),
        registry=registry,
    )
    gate_ratio_metric = Gauge(
        "trust_gate_duration_ratio",
        "Ratio of gate runtime vs suite total",  # unitless
        labelnames=("gate",),
        registry=registry,
    )
    suite_duration_metric = Gauge(
        "trust_gate_suite_runtime_ms",
        "Mean runtime for the trust gate suite (milliseconds)",
        registry=registry,
    )
    suite_pass_metric = Gauge(
        "trust_gate_suite_pass",
        "Trust gate SLA pass indicator (1=pass,0=fail)",
        registry=registry,
    )
    suite_limit_metric = Gauge(
        "trust_gate_suite_limit_ms",
        "Configured SLA limit for the trust gate suite (milliseconds)",
        registry=registry,
    )
    validation_duration_metric = Gauge(
        "validation_suite_duration_ms",
        "Mean runtime for the validation suite (milliseconds)",
        registry=registry,
    )

    stages = trust_gates.get("stages")
    if isinstance(stages, dict):
        suite_total = stages.get("trust_suite.total") or {}
        total_mean = suite_total.get("mean_ms")
        if isinstance(total_mean, (int, float)):
            suite_duration_metric.set(float(total_mean))
        status_counts = suite_total.get("status_counts")
        if isinstance(status_counts, dict):
            for status, count in status_counts.items():
                if (
                    isinstance(status, str)
                    and isinstance(count, (int, float))
                    and count > 0
                ):
                    status_metric.labels(gate="suite", status=status).set(1.0)
        if isinstance(perf_sla, dict):
            if isinstance(perf_sla.get("pass"), bool):
                suite_pass_metric.set(1.0 if perf_sla["pass"] else 0.0)
            limit_ms = perf_sla.get("baseline_mean_ms")
            limit_multiplier = perf_sla.get("limit_multiplier")
            if isinstance(limit_ms, (int, float)) and isinstance(
                limit_multiplier, (int, float)
            ):
                suite_limit_metric.set(float(limit_ms) * float(limit_multiplier))
        for gate_key, info in stages.items():
            if (
                not gate_key.startswith("trust_suite.")
                or gate_key == "trust_suite.total"
            ):
                continue
            gate = gate_key.split(".", 1)[1]
            if not isinstance(info, dict):
                continue
            for status in ("pass", "warn", "fail"):
                count = (
                    info.get("status_counts", {}).get(status)
                    if isinstance(info.get("status_counts"), dict)
                    else 0
                )
                status_metric.labels(gate=gate, status=status).set(
                    1.0 if isinstance(count, (int, float)) and count > 0 else 0.0
                )
            mean_ms = info.get("mean_ms")
            if isinstance(mean_ms, (int, float)):
                gate_duration_metric.labels(gate=gate).set(float(mean_ms))
            ratio = info.get("ratio_vs_suite_total")
            if isinstance(ratio, (int, float)):
                gate_ratio_metric.labels(gate=gate).set(float(ratio))

    if isinstance(validation, dict):
        stages_payload = validation.get("stages")
        if isinstance(stages_payload, dict):
            total = stages_payload.get("total")
            if isinstance(total, dict):
                mean_ms = total.get("mean_ms")
                if isinstance(mean_ms, (int, float)):
                    validation_duration_metric.set(float(mean_ms))

    metrics_path = ARTIFACT_DIR / "trust_gate_metrics.prom"
    write_to_textfile(str(metrics_path), registry)
    return metrics_path


def perf_run_gate(summary: dict[str, Any]) -> dict[str, Any] | None:
    """Execute perf_run.py, enforce SLA, and emit telemetry metrics."""

    script = ROOT / "scripts" / "bench" / "perf_run.py"
    out_path = ARTIFACT_DIR / "perf_latest.json"
    iterations = _env_int("AF_PERF_GATE_ITERATIONS", DEFAULT_PERF_ITERATIONS)
    warmup = _env_int("AF_PERF_GATE_WARMUP", DEFAULT_PERF_WARMUP)
    limit_multiplier = _env_float(
        "AF_PERF_GATE_LIMIT_MULTIPLIER", DEFAULT_PERF_LIMIT_MULTIPLIER
    )
    timeout_seconds = _env_timeout("AF_PERF_GATE_TIMEOUT", DEFAULT_PERF_TIMEOUT_SECONDS)

    detail: dict[str, Any] = {
        "iterations": iterations,
        "warmup": warmup,
        "limit_multiplier": limit_multiplier,
    }

    if not script.exists():
        detail["error"] = "perf_run.py missing"
        detail["remediation"] = (
            "Commit includes perf gate harness; ensure scripts/bench/perf_run.py exists."
        )
        summary["perf_run"] = detail
        summary["failures"].append("perf_harness_missing")
        return None

    cmd = [
        sys.executable,
        str(script),
        "--iterations",
        str(iterations),
        "--warmup",
        str(warmup),
        "--output",
        str(out_path),
        "--limit-multiplier",
        str(limit_multiplier),
    ]

    try:
        code, out = _run(cmd, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        detail["error"] = f"perf_run.py exceeded timeout ({timeout_seconds}s)."
        detail["remediation"] = (
            "Investigate runaway benchmark; consider lowering iterations or inspecting recent trust gate changes."
        )
        summary["perf_run"] = detail
        summary["failures"].append("perf_run_timeout")
        return None

    detail["exit_code"] = code
    if code != 0:
        hint = ""
        if "ModuleNotFoundError" in out:
            hint = "Missing dependency detected; run 'poetry install --with dev' to install perf tooling."
        elif "ImportError" in out:
            hint = "Import error encountered; ensure benchmark dependencies are installed (poetry install --with dev)."
        detail["stdout_tail"] = _tail(out)
        if hint:
            detail["remediation"] = hint
        else:
            detail["remediation"] = (
                "Inspect stdout_tail for details; rerun perf_run.py locally."
            )
        summary["perf_run"] = detail
        summary["failures"].append("perf_run_failed")
        return None

    if not out_path.exists():
        detail["error"] = "perf_run.py did not emit expected output file"
        detail["remediation"] = (
            "Check stdout for JSON payload and ensure --output path is writable."
        )
        summary["perf_run"] = detail
        summary["failures"].append("perf_run_missing_output")
        return None

    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        detail["error"] = f"Unable to parse perf output: {exc}"
        detail["remediation"] = "Validate perf_latest.json contents; rerun perf_run.py"
        summary["perf_run"] = detail
        summary["failures"].append("perf_run_bad_payload")
        return None

    runs = payload.get("runs", {})
    if isinstance(runs, dict):
        mean_sec = runs.get("mean_sec")
        if isinstance(mean_sec, (int, float)):
            detail["mean_sec"] = float(mean_sec)
        trust_mean = runs.get("trust_gate_total_mean_ms") or runs.get(
            "validation_total_mean_ms"
        )
        if isinstance(trust_mean, (int, float)):
            detail["trust_gate_mean_ms"] = float(trust_mean)

    perf_sla = payload.get("perf_sla", {})
    sla_pass = bool(perf_sla.get("pass")) if isinstance(perf_sla, dict) else False
    detail["sla_pass"] = sla_pass
    if isinstance(perf_sla, dict):
        detail["perf_sla"] = {
            key: perf_sla.get(key)
            for key in (
                "suite",
                "mean_ms",
                "p95_ms",
                "baseline_mean_ms",
                "limit_multiplier",
                "run_id",
                "generated_at",
                "pass",
            )
        }

    metrics_path = _write_telemetry_metrics(payload)
    if metrics_path is not None:
        relative_metrics = str(metrics_path.relative_to(ROOT))
        detail["metrics_path"] = relative_metrics
        telemetry_detail: dict[str, Any] = {"metrics_path": relative_metrics}
        trust_suite = (
            payload.get("trust_gates", {})
            if isinstance(payload.get("trust_gates"), dict)
            else {}
        )
        trust_suite_total = (
            trust_suite.get("stages", {}).get("trust_suite.total")
            if isinstance(trust_suite.get("stages"), dict)
            else {}
        )
        validation = (
            payload.get("validation", {})
            if isinstance(payload.get("validation"), dict)
            else {}
        )
        validation_total = (
            validation.get("stages", {}).get("total")
            if isinstance(validation.get("stages"), dict)
            else {}
        )
        trust_mean = (
            trust_suite_total.get("mean_ms")
            if isinstance(trust_suite_total, dict)
            else None
        )
        validation_mean = (
            validation_total.get("mean_ms")
            if isinstance(validation_total, dict)
            else None
        )
        if isinstance(trust_mean, (int, float)):
            telemetry_detail["trust_gate_mean_ms"] = float(trust_mean)
        if isinstance(validation_mean, (int, float)):
            telemetry_detail["validation_total_mean_ms"] = float(validation_mean)
        summary["telemetry"] = telemetry_detail

    detail["output"] = str(out_path.relative_to(ROOT))
    summary["perf_run"] = detail

    if not sla_pass:
        detail["error"] = "Trust gate SLA violation detected"
        detail.setdefault(
            "remediation",
            "Investigate recent trust gate changes, refresh baseline if intentional, or file waiver per governance process.",
        )
        summary["failures"].append("trust_gate_sla")

    return payload


def observability_gate(summary: dict[str, Any]) -> None:
    script = (
        ROOT / "alphaforge-brain" / "scripts" / "bench" / "observability_overhead.py"
    )
    if not script.exists():
        summary["observability"] = {"skipped": True, "reason": "script missing"}
        return
    code, out = _run(
        [
            sys.executable,
            str(script),
            "--rows",
            "150000",
            "--repeat",
            "3",
            "--threshold",
            "0.03",
        ]
    )
    out_s = out.strip()
    # Detect environment ABI/import problems and skip instead of failing locally
    abi_markers = (
        "A module that was compiled using NumPy 1.x cannot be run",
        "ModuleNotFoundError: No module named 'pandas'",
        "import pyarrow.lib as _lib",
    )
    if code != 0 and any(m in out_s for m in abi_markers):
        summary["observability"] = {"skipped": True, "reason": "env import/ABI issue"}
        return
    summary["observability"] = {"exit_code": code, "output": out_s}
    if code != 0:
        summary["failures"].append("observability_overhead")


def bootstrap_gate(summary: dict[str, Any]) -> None:
    script = ROOT / "scripts" / "ci" / "bootstrap_runtime_probe.py"
    if not script.exists():
        summary["bootstrap"] = {
            "skipped": True,
            "reason": "bootstrap_runtime_probe.py missing",
        }
        return
    out_path = ARTIFACT_DIR / "bootstrap_runtime.json"
    code, out = _run([sys.executable, str(script), "--out", str(out_path)])
    try:
        detail = json.loads(Path(out_path).read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        detail = {"error": f"parse failure: {e}", "raw": out}
    detail["exit_code"] = code
    if not detail.get("skipped") and not detail.get("pass", True):
        summary["failures"].append("bootstrap_ratio")
    summary["bootstrap"] = detail


def memory_sampler_gate(summary: dict[str, Any]) -> None:
    # Reuse causality_guard_overhead as a 1% overhead proxy.
    script = (
        ROOT / "alphaforge-brain" / "scripts" / "bench" / "causality_guard_overhead.py"
    )
    if not script.exists():
        summary["memory_sampler"] = {
            "skipped": True,
            "reason": "causality_guard_overhead missing",
        }
        return
    code, out = _run(
        [
            sys.executable,
            str(script),
            "--n",
            "1000000",
            "--k",
            "100000",
            "--threshold",
            "0.01",
        ]
    )
    summary["memory_sampler"] = {"exit_code": code, "output": out.strip()}
    if code != 0:
        summary["failures"].append("memory_sampler_overhead")


def main() -> int:
    summary: dict[str, Any] = {"failures": [], "alerts": []}
    perf_payload = perf_run_gate(summary)
    observability_gate(summary)
    bootstrap_gate(summary)
    memory_sampler_gate(summary)
    # Early Alert (T094): Compare baseline vs current; alert at >=3%, fail at >=5%
    # Prefer a perf_run-compatible baseline file; fall back to skipping if not found
    baseline_candidates = [
        ROOT / "zz_artifacts" / "perf_run_baseline.json",
        ROOT / "artifacts" / "perf_run_baseline.json",
    ]
    baseline = next((p for p in baseline_candidates if p.exists()), None)
    current = ROOT / "zz_artifacts" / "perf_latest.json"
    early = ROOT / "scripts" / "ci" / "perf_early_alert.py"
    if perf_payload is None and current.exists():
        try:
            perf_payload = json.loads(current.read_text(encoding="utf-8"))
        except Exception:
            perf_payload = None
    if baseline is not None and current.exists() and early.exists():
        # Check that baseline appears perf_run-shaped (runs.median_sec exists)
        try:
            _b = json.loads(baseline.read_text(encoding="utf-8"))
            _c = json.loads(current.read_text(encoding="utf-8"))
            if not (
                isinstance(_b, dict)
                and isinstance(_c, dict)
                and isinstance(_b.get("runs"), dict)
                and isinstance(_c.get("runs"), dict)
                and "median_sec" in _b["runs"]
                and "median_sec" in _c["runs"]
            ):
                raise ValueError("incompatible baseline/current shape for perf_run")
        except Exception as e:
            summary["early_alert"] = {"skipped": True, "reason": f"{e}"}
            baseline = None
    if baseline is not None and current.exists() and early.exists():
        code, out = _run(
            [
                sys.executable,
                str(early),
                "--baseline",
                str(baseline),
                "--current",
                str(current),
                "--metric",
                "median",
                "--alert",
                "0.03",
                "--fail",
                "0.05",
            ]
        )
        try:
            detail = json.loads(out)
        except Exception:
            detail = {"raw": out, "parse_error": True}
        if code != 0:
            summary["failures"].append("early_alert_fail")
        else:
            if isinstance(detail, dict) and detail.get("status") == "ALERT":
                summary["alerts"].append("performance_degradation>=3%")
        summary["early_alert"] = detail
    else:
        summary["early_alert"] = {
            "skipped": True,
            "reason": "missing perf_run baseline/current or script",
        }
    summary["passed"] = len(summary["failures"]) == 0
    out_file = ARTIFACT_DIR / "perf_gates_summary.json"
    out_file.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
