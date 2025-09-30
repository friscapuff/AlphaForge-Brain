#!/usr/bin/env python
"""Run each logical test directory in isolation collecting separate coverage data files.

This script helps produce a combined, de-duplicated coverage report while
surfacing per-slice duration and exit status (pass/fail/timeout).

Strategy
--------
For every test directory discovered (mirrors logic in run_test_slices.py):
  * Set a distinct COVERAGE_FILE (e.g. .coverage.slice_unit)
  * Invoke pytest with --cov pointing at project sources and with reporting disabled
  * On completion (or timeout) record duration + status
After all slices:
  * coverage combine (merges the .coverage.slice_* files)
  * coverage xml (writes coverage.xml)
  * coverage report -m (stdout summary for local convenience)

Usage
-----
python scripts/run_coverage_slices.py [timeout_seconds]

Optional env vars:
  AF_COV_SOURCES   Comma separated coverage source paths (default: alphaforge-brain/src)
  AF_COV_REPORT    If set (non-empty) adds a terminal report per slice (slower)

Exit code is non-zero if any slice fails or times out.

Notes
-----
The per-slice COVERAGE_FILE naming avoids needing --cov-append which can
produce contention / partial writes under abrupt termination scenarios.
Combining at the end yields a canonical aggregate reflecting all executed code.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_SOURCES = os.environ.get("AF_COV_SOURCES", "alphaforge-brain/src")

TEST_ROOTS: list[Path] = []
brain_tests = ROOT / "alphaforge-brain" / "tests"
if brain_tests.exists():
    for p in sorted(brain_tests.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        if name == "__pycache__" or name.startswith("."):
            continue
        # Skip directories that contain no test files (heuristic: any file starting with test_)
        has_tests = any(
            child.name.startswith("test_") for child in p.iterdir() if child.is_file()
        )
        if not has_tests:
            continue
        TEST_ROOTS.append(p)

parallel_tests = ROOT / "tests"
if parallel_tests.exists():
    for p in sorted(parallel_tests.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        if name == "__pycache__" or name.startswith("."):
            continue
        has_tests = any(
            child.name.startswith("test_") for child in p.iterdir() if child.is_file()
        )
        if not has_tests:
            continue
        TEST_ROOTS.append(p)

SLICE_TIMEOUT = (
    int(float(sys.argv[1])) if len(sys.argv) > 1 else 600
)  # generous default
PYTEST_BASE = [
    sys.executable,
    "-m",
    "pytest",
    "-q",
    f"--cov={PROJECT_SOURCES}",
    "--maxfail=1",
]
REPORT_PER_SLICE = bool(os.environ.get("AF_COV_REPORT"))
if not REPORT_PER_SLICE:
    # Disable terminal & XML reports per slice for speed; final aggregate will produce them.
    PYTEST_BASE += ["--cov-report="]

results = []
coverage_files: list[Path] = []
for directory in TEST_ROOTS:
    label = directory.name.replace("-", "_")
    cov_file = ROOT / f".coverage.slice_{label}"
    env = os.environ.copy()
    env["COVERAGE_FILE"] = str(cov_file)
    start = time.time()
    status = "pass"
    detail_tail = None
    try:
        proc = subprocess.run(
            [*PYTEST_BASE, str(directory)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=SLICE_TIMEOUT,
            text=True,
        )
        if proc.returncode != 0:
            status = "fail"
            detail_tail = proc.stdout[-2000:]
    except subprocess.TimeoutExpired as e:
        status = "timeout"
        detail_tail = (e.stdout or "")[-2000:]
    duration = round(time.time() - start, 2)
    if Path(cov_file).exists():
        coverage_files.append(cov_file)
    results.append(
        {
            "directory": str(directory.relative_to(ROOT)),
            "status": status,
            "duration_sec": duration,
            "coverage_file": str(cov_file),
            "detail_tail": detail_tail,
        }
    )
    print(f"{status:8} {duration:6.2f}s  {directory.relative_to(ROOT)}")

# Write slice summary JSON
summary_path = ROOT / "coverage_slice_results.json"
summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Wrote {summary_path} ({len(results)} slices)")

# Combine coverage if all (or some) produced data
if coverage_files:
    print("Combining coverage data files ...")
    combine = subprocess.run([sys.executable, "-m", "coverage", "combine"], cwd=ROOT)
    if combine.returncode != 0:
        print("WARNING: coverage combine returned non-zero exit code", file=sys.stderr)
    # Generate XML + terminal report
    subprocess.run([sys.executable, "-m", "coverage", "xml"], cwd=ROOT)
    subprocess.run([sys.executable, "-m", "coverage", "report", "-m"], cwd=ROOT)
    print("Aggregate coverage artifacts written: coverage.xml + terminal summary above")
else:
    print("No coverage data files were produced; skipping combine.")

# Non-zero exit if any problematic slice
if any(r["status"] != "pass" for r in results):
    sys.exit(1)
