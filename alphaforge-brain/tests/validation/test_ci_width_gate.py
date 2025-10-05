from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain.artifacts.writer import write_artifacts


def test_ci_width_gate_script_smoke(tmp_path: Path) -> None:
    # Create minimal run dir with validation.json containing bootstrap ci
    run_hash = "RUNX"
    run_dir = tmp_path / "artifacts" / run_hash
    run_dir.mkdir(parents=True)
    validation = {
        "summary": {},
        "bootstrap": {
            "ci": [0.01, 0.03],
            "method": "hadj_bb",
            "trials": 100,
            "fallback": False,
        },
        "p_values": {},
    }
    (run_dir / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
    (run_dir / "summary.json").write_text("{}", encoding="utf-8")
    (run_dir / "metrics.json").write_text("{}", encoding="utf-8")

    # Ensure writer can build a manifest too (side check)
    record: dict[str, Any] = {
        "summary": {},
        "validation_raw": {
            "block_bootstrap": {
                "ci": [0.01, 0.03],
                "method": "hadj_bb",
                "trials": 100,
                "fallback": False,
            }
        },
    }
    write_artifacts(run_hash, record, base_path=tmp_path / "artifacts")

    # Run the CI gate script in both modes with threshold
    import subprocess
    import sys

    script = Path(__file__).parents[2] / "scripts" / "ci" / "bootstrap_ci_width_gate.py"
    # Passing case (threshold higher)
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            str(run_dir),
            "--threshold",
            "0.05",
            "--mode",
            "STRICT",
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    assert "PASS" in (cp.stdout + cp.stderr)
    # Failing case (threshold lower)
    cp2 = subprocess.run(
        [
            sys.executable,
            str(script),
            str(run_dir),
            "--threshold",
            "0.01",
            "--mode",
            "STRICT",
        ],
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 1
    assert "exceeds threshold" in (cp2.stdout + cp2.stderr)
