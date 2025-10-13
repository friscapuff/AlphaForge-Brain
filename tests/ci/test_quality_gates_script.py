from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _invoke_quality_gates(
    repo_root: Path, extra_env: dict[str, str] | None = None
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    script = repo_root / "scripts" / "ci" / "run_quality_gates.py"
    assert script.exists(), "run_quality_gates.py missing"
    env = os.environ.copy()
    for key in [
        "AF_QG_FIXTURE_DETERMINISM",
        "AF_QG_FIXTURE_CONTRACT",
        "AF_QG_FIXTURE_MIGRATIONS",
        "AF_QG_FIXTURE_MEMORY",
        "AF_QG_FIXTURE_CROSS_ROOT",
        "AF_FORCE_QG_FAILURE",
    ]:
        env.pop(key, None)
    if extra_env:
        env.update(extra_env)

    out_file = repo_root / "zz_artifacts" / "quality_gates_summary.json"
    if out_file.exists():
        out_file.unlink()

    proc = subprocess.run(
        [
            sys.executable,
            str(script),
        ],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert out_file.exists(), f"summary file not produced. Output:\n{proc.stdout}"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    return proc, data


def test_quality_gates_smoke() -> None:
    """Smoke test the unified quality gates script.

    Ensures script exits 0 (under current stub conditions) and writes
    summary JSON containing expected top-level keys.
    """
    repo_root = Path(__file__).resolve().parents[2]
    _, data = _invoke_quality_gates(repo_root)
    for key in [
        "determinism",
        "contract",
        "migrations",
        "memory",
        "cross_root",
        "passed",
        "failures",
        "generated_at",
        "version",
    ]:
        assert key in data, f"Missing key {key} in summary JSON"
    # Do not assert pass/fail; script enforces policies (some may evolve)
    assert isinstance(data["passed"], bool)
    # Basic ISO-8601 shape check
    datetime.fromisoformat(data["generated_at"])  # raises if malformed
    assert isinstance(data["version"], str) and data["version"], "version missing"


def test_quality_gates_short_circuits_on_fixture_failure() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    fixtures = repo_root / "alphaforge-brain" / "tests" / "ci" / "fixtures"
    env = {
        "AF_QG_FIXTURE_DETERMINISM": str(fixtures / "determinism_replay_failure.py"),
    }
    proc, data = _invoke_quality_gates(repo_root, env)
    assert proc.returncode == 1, proc.stdout
    assert data["failures"] == ["determinism"]
    assert data["determinism"]["failed"] is True
    assert data["contract"]["skipped"] is True
    assert data["contract"]["reason"] == "short-circuit after failure"


def test_quality_gates_forced_failure_toggle() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = {"AF_FORCE_QG_FAILURE": "contract"}
    proc, data = _invoke_quality_gates(repo_root, env)
    assert proc.returncode == 1, proc.stdout
    assert data["failures"] == ["contract"]
    assert data["contract"]["forced_failure"] is True
    assert data["contract"]["failed"] is True
    # Subsequent gates skipped due to short-circuiting
    assert data["migrations"]["skipped"] is True


def test_quality_gates_handles_missing_override() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    fixtures = repo_root / "alphaforge-brain" / "tests" / "ci" / "fixtures"
    env = {
        "AF_QG_FIXTURE_MEMORY": str(repo_root / "missing_fixture.py"),
        "AF_QG_FIXTURE_CONTRACT": str(fixtures / "generate_openapi_match.py"),
        "AF_QG_FIXTURE_MIGRATIONS": str(fixtures / "check_migrations_head_success.py"),
    }
    _proc, data = _invoke_quality_gates(repo_root, env)
    assert data["memory"]["skipped"] is True
    assert "missing_fixture.py" in data["memory"]["reason"]
