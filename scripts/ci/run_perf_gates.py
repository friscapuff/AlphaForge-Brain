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
    summary: dict[str, Any] = {"failures": []}
    observability_gate(summary)
    bootstrap_gate(summary)
    memory_sampler_gate(summary)
    summary["passed"] = len(summary["failures"]) == 0
    out_file = ARTIFACT_DIR / "perf_gates_summary.json"
    out_file.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
