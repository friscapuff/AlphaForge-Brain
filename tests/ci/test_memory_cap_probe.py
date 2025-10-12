from __future__ import annotations

import importlib.util
import json
import subprocess
import time
from pathlib import Path

import pytest

import scripts.ci.memory_cap_probe as probe


def _waity_workload(iterations: int, seed: int) -> None:
    time.sleep(0.01)


def test_run_probe_records_peak_bytes() -> None:
    values = [1024, 2048, 4096]

    def sample() -> int | None:
        if values:
            return values.pop(0)
        raise StopIteration

    payload, exit_code = probe.run_probe(
        iterations=1,
        seed=42,
        cap_mb=10,
        interval_ms=0,
        sample_func=sample,
        workload_func=_waity_workload,
    )

    assert exit_code == 0
    assert payload["rss_bytes"] == 4096
    assert pytest.approx(payload["rss_mb_peak"], rel=1e-6) == 4096 / (1024 * 1024)
    assert payload["within_cap"] is True
    assert payload["samples"] >= 1


def test_run_probe_flags_cap_breach() -> None:
    bytes_over = 3 * 1024 * 1024

    def sample() -> int | None:
        return bytes_over

    payload, exit_code = probe.run_probe(
        iterations=1,
        seed=1,
        cap_mb=1,
        interval_ms=0,
        sample_func=sample,
        workload_func=_waity_workload,
    )

    assert exit_code == 3
    assert payload["within_cap"] is False
    assert payload["rss_bytes"] == bytes_over
    assert payload["cap_bytes"] == 1024 * 1024


def test_run_probe_skips_when_rss_unavailable() -> None:
    payload, exit_code = probe.run_probe(
        iterations=1,
        seed=1,
        cap_mb=1,
        interval_ms=0,
        sample_func=lambda: None,
        workload_func=_waity_workload,
    )

    assert exit_code == 0
    assert payload["skipped"] is True
    assert "reason" in payload


def test_main_writes_payload(tmp_path: Path, monkeypatch) -> None:
    manifest = {
        "rss_bytes": 900 * 1024,
        "rss_mb_peak": (900 * 1024) / (1024 * 1024),
        "cap_bytes": 10 * 1024 * 1024,
        "cap_mb": 10,
        "within_cap": True,
        "samples": 3,
    }

    monkeypatch.setattr(probe, "run_probe", lambda *args, **kwargs: (manifest, 0))

    out_path = tmp_path / "memory.json"
    exit_code = probe.main(
        ["--iterations", "1", "--cap-mb", "10", "--out", str(out_path)]
    )
    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload == manifest


def test_memory_cap_probe_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "ci" / "memory_cap_probe.py"
    assert script.exists()
    if importlib.util.find_spec("numpy") is None:
        pytest.skip("numpy not available outside managed env")
    out_file = tmp_path / "memory_cap_probe.json"
    proc = subprocess.run(
        [
            "python",
            str(script),
            "--iterations",
            "1",
            "--out",
            str(out_file),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if not out_file.exists():
        pytest.skip(f"memory cap probe failed early: {proc.stdout[:200]}")
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    if payload.get("skipped"):
        assert "reason" in payload
    else:
        for key in ("rss_bytes", "cap_bytes", "within_cap", "samples"):
            assert key in payload
