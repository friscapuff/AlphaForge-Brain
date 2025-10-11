from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.cli
def test_trust_gates_cli_provides_subset_and_report_flags(tmp_path: Path) -> None:
    """FR-201/FR-213: CLI must expose --only flag and report directory output."""

    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "alphaforge-brain" / "src")}
    cmd = [sys.executable, "-m", "cli.trust_gates", "--help"]
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env)

    assert completed.returncode == 0, completed.stderr
    stdout = completed.stdout
    assert "--only" in stdout
    assert "trust_gate_report" in stdout
