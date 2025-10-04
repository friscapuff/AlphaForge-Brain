from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_perf_gates_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "ci" / "run_perf_gates.py"
    assert script.exists(), "run_perf_gates.py missing"
    proc = subprocess.run(
        [
            "python",
            str(script),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out_file = repo_root / "zz_artifacts" / "perf_gates_summary.json"
    assert out_file.exists(), f"perf summary not produced. Output:\n{proc.stdout}"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    for key in ["observability", "bootstrap", "memory_sampler", "failures", "passed"]:
        assert key in data, f"Missing key {key} in perf summary"
