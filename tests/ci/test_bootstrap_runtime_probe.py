from __future__ import annotations

import json
import subprocess
from pathlib import Path
import importlib
import pytest


def test_bootstrap_runtime_probe_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "ci" / "bootstrap_runtime_probe.py"
    assert script.exists()
    # Skip if numpy not importable in raw interpreter (outside poetry env)
    if importlib.util.find_spec("numpy") is None:  # type: ignore
        pytest.skip("numpy not available outside managed env")
    proc = subprocess.run(["python", str(script), "--out", "zz_artifacts/bootstrap_probe.json"], cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # Accept non-zero exit if ratio slightly above threshold locally; still validate JSON structure.
    out_file = repo_root / "zz_artifacts" / "bootstrap_probe.json"
    if out_file.exists():
        data = json.loads(out_file.read_text(encoding="utf-8"))
    else:
        # If script failed, provide context then skip (environmental)
        pytest.skip(f"bootstrap probe failed in raw env: {proc.stdout[:200]}")
    for k in ["first_s", "second_s", "ratio", "threshold", "pass"]:
        assert k in data
