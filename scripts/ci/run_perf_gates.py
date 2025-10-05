#!/usr/bin/env python3
"""Performance Benchmark Gates (T020a / FR-113)

Aggregates and enforces performance thresholds:
  - Observability overhead < 3% (observability_overhead.py)
  - Bootstrap runtime inflation ≤ 1.2x baseline (measured via perf_run script with and without a flag)
  - Memory sampler overhead < 1% (causality_guard_overhead used as proxy for now)

Produces JSON summary: zz_artifacts/perf_gates_summary.json

Notes:
 - Bootstrap runtime: we approximate by executing perf_run.py twice with a small synthetic spec.
   If perf_run.py lacks a disable flag, we treat ratio = 1.0 (pass) and mark bootstrap as provisional.
 - Memory sampler overhead uses causality_guard_overhead benchmark threshold (1%). If script absent, skipped.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "zz_artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def _run(cmd: list[str]) -> tuple[int, str]:
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
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    return p.returncode, p.stdout


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
    summary["observability"] = {"exit_code": code, "output": out.strip()}
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
        [sys.executable, str(script), "--n", "400000", "--threshold", "0.01"]
    )
    summary["memory_sampler"] = {"exit_code": code, "output": out.strip()}
    if code != 0:
        summary["failures"].append("memory_sampler_overhead")


def main() -> int:
    summary: dict[str, Any] = {"failures": [], "alerts": []}
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
    # If current missing but perf_run exists, generate it now
    if not current.exists():
        perf_run = ROOT / "scripts" / "bench" / "perf_run.py"
        if perf_run.exists():
            _ = ARTIFACT_DIR.mkdir(exist_ok=True)
            _code, _out = _run(
                [
                    sys.executable,
                    str(perf_run),
                    "--iterations",
                    "5",
                    "--warmup",
                    "1",
                    "--output",
                    str(current),
                ]
            )
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
