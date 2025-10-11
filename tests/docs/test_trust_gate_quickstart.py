from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FEATURE_DIR = Path(__file__).resolve().parents[2] / "specs" / "011-trust-gate-framework"
QUICKSTART_PATH = FEATURE_DIR / "quickstart.md"


@pytest.mark.docs
def test_quickstart_commands_align_with_cli_entrypoint() -> None:
    """FR-212: Quickstart must document runnable trust gate CLI commands."""

    content = QUICKSTART_PATH.read_text(encoding="utf-8")
    assert "poetry run trust-gates" in content, "Quickstart missing trust gate command"

    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "alphaforge-brain" / "src")}
    cmd = [sys.executable, "-m", "cli.trust_gates", "--help"]

    completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert (
        completed.returncode == 0
    ), f"trust-gates CLI help failed: {completed.stderr or completed.stdout}"
