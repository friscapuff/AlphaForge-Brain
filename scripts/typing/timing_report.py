#!/usr/bin/env python
"""Measure wall-clock time for ruff + mypy and write JSON + markdown summary.

Usage:
  poetry run python scripts/typing/timing_report.py --out-json typing_timing.json --out-md typing_timing.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict


class CmdResult(TypedDict):
    label: str
    cmd: Sequence[str]
    returncode: int
    duration_sec: float
    stdout: str
    stderr: str


def run_cmd(label: str, cmd: list[str]) -> CmdResult:
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    end = time.perf_counter()
    return {
        "label": label,
        "cmd": cmd,
        "returncode": proc.returncode,
        "duration_sec": round(end - start, 4),
        "stdout": proc.stdout[-4000:],  # tail safeguard
        "stderr": proc.stderr[-4000:],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--paths", nargs="*", default=["src"])
    ns = ap.parse_args(argv)

    results: list[CmdResult] = []
    results.append(run_cmd("ruff_check", [sys.executable, "-m", "ruff", "check", "."]))
    results.append(run_cmd("mypy", [sys.executable, "-m", "mypy", *ns.paths]))

    summary = {
        "total_duration_sec": round(sum(r["duration_sec"] for r in results), 4),
        "results": results,
    }
    Path(ns.out_json).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# Typing & Lint Timing",
        "",
        f"Total: {summary['total_duration_sec']}s",
        "",
    ]
    for r in results:
        md_lines.append(f"- {r['label']}: {r['duration_sec']}s (rc={r['returncode']})")
    Path(ns.out_md).write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print("\n".join(md_lines))

    # Non-zero if any command failed
    if any(r["returncode"] != 0 for r in results):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
