from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.perf
@pytest.mark.timeout(120)
def test_trust_gate_suite_runtime(tmp_path):
    """Trust gate suite runtime should remain within 1.5x Masters baseline."""

    repo_root = Path(__file__).resolve().parents[3]
    output_path = tmp_path / "perf_output.json"

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "bench" / "perf_run.py"),
        "--iterations",
        "3",
        "--warmup",
        "1",
        "--output",
        str(output_path),
    ]

    env = os.environ.copy()
    result = subprocess.run(
        cmd,
        check=True,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert output_path.exists(), (
        "Benchmark harness did not produce output file.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    trust_gates_section = payload.get("trust_gates", {})
    suite_stats = trust_gates_section.get("stages", {}).get("trust_suite.total")
    assert isinstance(suite_stats, dict) and suite_stats.get("mean_ms") is not None, (
        "Trust gate suite runtime missing from benchmark output.\n"
        f"payload snippet: {json.dumps(trust_gates_section, indent=2)}"
    )
    trust_suite_mean = suite_stats["mean_ms"]

    baseline_path = repo_root / "artifacts" / "perf_baseline.json"
    baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_mean = baseline_data.get("summary", {}).get("mean_ms")
    assert baseline_mean is not None, "Baseline file missing summary.mean_ms"

    sla_record = payload.get("perf_sla")
    assert isinstance(sla_record, dict), "perf_sla record missing from benchmark output"
    assert sla_record.get("suite") == "trust_gates"
    assert (
        isinstance(sla_record.get("run_id"), str) and sla_record["run_id"]
    ), "perf_sla.run_id missing"
    generated_at = sla_record.get("generated_at")
    assert isinstance(generated_at, str) and generated_at.endswith(
        "Z"
    ), "perf_sla.generated_at must be UTC ISO string"

    assert sla_record.get("mean_ms") == pytest.approx(trust_suite_mean)

    baseline_from_record = sla_record.get("baseline_mean_ms")
    if baseline_from_record is not None:
        assert baseline_from_record == pytest.approx(baseline_mean)

    limit_multiplier = sla_record.get("limit_multiplier")
    assert limit_multiplier == pytest.approx(1.5)

    assert (
        sla_record.get("pass") is True
    ), "perf_sla.pass should be true when suite meets SLA"

    limit = baseline_mean * 1.5
    assert (
        trust_suite_mean <= limit
    ), f"Trust gate suite runtime {trust_suite_mean}ms exceeds limit {limit}ms"

    suite_status_counts = trust_gates_section.get("suite_status_counts", {})
    assert suite_status_counts.get("fail", 0) == 0, (
        "Trust gate suite reported failures despite runtime guard passing.\n"
        f"Counts: {suite_status_counts}"
    )
