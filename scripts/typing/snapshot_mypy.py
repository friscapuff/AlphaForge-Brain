#!/usr/bin/env python
"""Capture a mypy error snapshot (JSON) for CI comparison.

Usage:
  poetry run python scripts/typing/snapshot_mypy.py --output .mypy_snapshot.json [--paths src tests]

If mypy exits non-zero, we still capture output and forward the exit code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_mypy(paths: list[str]) -> tuple[int, str]:
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--hide-error-context",
        "--no-color-output",
        "--no-error-summary",
        *paths,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Combine stdout + stderr (mypy prints to stdout mostly)
    output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--output", "-o", default=".mypy_snapshot.json", help="Snapshot JSON path"
    )
    p.add_argument(
        "--paths", nargs="*", default=["src"], help="Paths to check (default: src)"
    )
    p.add_argument(
        "--allow-nonzero",
        action="store_true",
        help="Do not exit non-zero if mypy fails (still record)",
    )
    return p.parse_args()


def snapshot() -> int:
    ns = parse_args()
    code, raw = run_mypy(ns.paths)
    # Parse lines of form: path:line:col: type: message
    errors = []
    for line in raw.splitlines():
        if not line or ":" not in line:
            continue
        # naive parse; mypy format stable enough for snapshot diffing
        parts = (
            line.split("::", 1)[0].split(":", 4)
            if line.count(":") >= 4
            else line.split(":", 4)
        )  # tolerate edge cases
        if len(parts) < 5:
            continue
        path, line_no, col_no, err_type, message = parts
        errors.append(
            {
                "path": path.strip(),
                "line": int(line_no),
                "col": int(col_no),
                "type": err_type.strip(),
                "message": message.strip(),
            }
        )
    snapshot = {"paths": ns.paths, "error_count": len(errors), "errors": errors}
    out_path = Path(ns.output)
    out_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote mypy snapshot to {out_path} with {len(errors)} errors")
    if code != 0 and not ns.allow_nonzero:
        return code
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(snapshot())
