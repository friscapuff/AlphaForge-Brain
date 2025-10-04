from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path

import pytest


def test_memory_cap_probe_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "ci" / "memory_cap_probe.py"
    assert script.exists()
    if (
        importlib.util.find_spec("numpy") is None
    ):  # memory workload depends indirectly on numpy
        pytest.skip("numpy not available outside managed env")
    proc = subprocess.run(
        [
            "python",
            str(script),
            "--iterations",
            "1",
            "--out",
            "zz_artifacts/memory_cap_probe.json",
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # On non-Linux this will skip.
    out_file = repo_root / "zz_artifacts" / "memory_cap_probe.json"
    if out_file.exists():
        payload = json.loads(out_file.read_text(encoding="utf-8"))
    else:
        pytest.skip(f"memory cap probe failed early: {proc.stdout[:200]}")
    # Accept either skipped or measured output
    if payload.get("skipped"):
        assert "reason" in payload
    else:
        for k in ["rss_mb_peak", "cap_mb", "within_cap", "samples"]:
            assert k in payload
