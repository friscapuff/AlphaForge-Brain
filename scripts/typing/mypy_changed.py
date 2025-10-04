#!/usr/bin/env python
"""Run mypy only on changed (staged) Python files, enforcing strict mode.

If no Python files are staged, exits successfully.

Usage (pre-commit local hook invokes without args):
  python scripts/typing/mypy_changed.py --strict
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path


def git_diff_names() -> list[str]:
    """Return staged Python file paths with meaningful content changes.

    We intentionally exclude renames and pure additions during bulk migrations
    to keep pre-commit latency reasonable and avoid blocking on legacy typing.
    Only files with an explicit Modified status (M) are returned.
    """
    cmd = ["git", "diff", "--cached", "--name-status", "-z"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    out = proc.stdout.decode("utf-8", errors="ignore")
    parts = [p for p in out.split("\x00") if p]
    files: list[str] = []
    i = 0
    while i < len(parts):
        status = parts[i]
        # Renames have two paths following the status token (Rxxx), handle generically
        if status.startswith("R") or status.startswith("C"):
            # Treat copies/renames as non-blocking in migration: exclude from strict run
            i += 3
            continue
        path = parts[i + 1] if i + 1 < len(parts) else ""
        if status.startswith("M"):
            files.append(path)
        # Exclude Added (A) and Deleted (D) from strict checks for bulk moves
        i += 2
    return files


def filter_py(files: Iterable[str]) -> list[str]:
    return [f for f in files if f.endswith(".py") and Path(f).is_file()]


def run_mypy(files: list[str], strict: bool) -> int:
    if not files:
        print("No Python files staged; skipping mypy.")
        return 0
    base_cmd = [sys.executable, "-m", "mypy"]
    if strict:
        base_cmd.append("--strict")
    base_cmd.extend(files)
    print("Running:", " ".join(base_cmd))
    proc = subprocess.run(base_cmd)
    return proc.returncode


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Enable mypy --strict")
    ap.add_argument(
        "--root-only",
        action="store_true",
        help="Only include files under alphaforge-brain/src",
    )
    ns = ap.parse_args(argv)
    changed = git_diff_names()
    py_files = filter_py(changed)
    if ns.root_only:
        py_files = [f for f in py_files if f.startswith("alphaforge-brain/src/")]
    rc = run_mypy(py_files, ns.strict)
    return rc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
