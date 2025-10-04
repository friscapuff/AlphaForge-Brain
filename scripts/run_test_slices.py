#!/usr/bin/env python
"""Run test directories in isolation with per-slice timeout.

Creates test_slice_results.json summarizing pass/fail/timeout and duration.
Intended to diagnose perceived hangs in full-suite runs.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_ROOTS: list[Path] = []

# Primary test root inside alphaforge-brain
brain_tests = ROOT / "alphaforge-brain" / "tests"
if brain_tests.exists():
    for p in sorted(brain_tests.iterdir()):
        if (
            p.is_dir() and (p / "__init__.py").exists()
        ) or p.is_dir():  # include even w/o __init__
            TEST_ROOTS.append(p)

# Optional top-level tests directory (parallel) if exists
parallel_tests = ROOT / "tests"
if parallel_tests.exists():
    for p in sorted(parallel_tests.iterdir()):
        if p.is_dir():
            TEST_ROOTS.append(p)

SLICE_TIMEOUT = (
    int(float(sys.argv[1])) if len(sys.argv) > 1 else 120
)  # seconds per slice
PYTEST_BASE = [sys.executable, "-m", "pytest", "-q", "--maxfail=1"]

results: list[dict[str, object]] = []
for directory in TEST_ROOTS:
    start = time.time()
    proc = None
    status = "pass"
    detail: str | None = None
    try:
        proc = subprocess.run(
            [*PYTEST_BASE, str(directory)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=SLICE_TIMEOUT,
            text=True,
        )
        if proc.returncode != 0:
            status = "fail"
            detail = proc.stdout[-2000:]
    except subprocess.TimeoutExpired as e:
        status = "timeout"
        raw = e.stdout
        if isinstance(raw, bytes):  # ensure str for typing
            raw_text = raw.decode(errors="replace")
        else:
            raw_text = raw or ""
        detail = raw_text[-2000:]
    duration = round(time.time() - start, 2)
    results.append(
        {
            "directory": str(directory.relative_to(ROOT)),
            "status": status,
            "duration_sec": duration,
            "detail_tail": detail,
        }
    )

out_path = ROOT / "test_slice_results.json"
out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Wrote {out_path} with {len(results)} slice results")
for r in results:
    print(f"{r['status']:8} {r['duration_sec']:6.2f}s  {r['directory']}")

# Non-zero exit if any fail or timeout
if any(r["status"] != "pass" for r in results):
    sys.exit(1)
