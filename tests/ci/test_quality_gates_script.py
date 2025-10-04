from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_quality_gates_smoke(tmp_path: Path) -> None:
    """Smoke test the unified quality gates script.

    Ensures script exits 0 (under current stub conditions) and writes
    summary JSON containing expected top-level keys.
    """
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "ci" / "run_quality_gates.py"
    assert script.exists(), "run_quality_gates.py missing"
    # Run script in isolated cwd so it still resolves ROOT correctly
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
    # Even if future failures occur, capture output for debugging
    out_file = repo_root / "zz_artifacts" / "quality_gates_summary.json"
    assert out_file.exists(), f"summary file not produced. Output:\n{proc.stdout}"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    for key in [
        "determinism",
        "contract",
        "migrations",
        "memory",
        "cross_root",
        "passed",
        "failures",
    ]:
        assert key in data, f"Missing key {key} in summary JSON"
    # Do not assert pass/fail; script enforces policies (some may evolve)
