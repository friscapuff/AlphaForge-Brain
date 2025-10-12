from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_perf_gates_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "ci" / "run_perf_gates.py"
    assert script.exists(), "run_perf_gates.py missing"
    env = os.environ.copy()
    env.setdefault("AF_PERF_GATE_ITERATIONS", "1")
    env.setdefault("AF_PERF_GATE_WARMUP", "0")
    proc = subprocess.run(
        [
            "python",
            str(script),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    out_file = repo_root / "zz_artifacts" / "perf_gates_summary.json"
    assert out_file.exists(), f"perf summary not produced. Output:\n{proc.stdout}"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    for key in [
        "perf_run",
        "observability",
        "bootstrap",
        "memory_sampler",
        "failures",
        "passed",
    ]:
        assert key in data, f"Missing key {key} in perf summary"
    perf_detail = data["perf_run"]
    assert perf_detail.get("sla_pass") is not False, f"Perf SLA failed: {perf_detail}"
    metrics_file = repo_root / "zz_artifacts" / "trust_gate_metrics.prom"
    assert metrics_file.exists(), "Prometheus metrics snapshot missing"
    metrics_text = metrics_file.read_text(encoding="utf-8")
    assert "trust_gate_status" in metrics_text
    assert "validation_suite_duration_ms" in metrics_text
