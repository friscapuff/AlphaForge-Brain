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
    cmd = ["git", "diff", "--cached", "--name-only"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
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
    ns = ap.parse_args(argv)
    changed = git_diff_names()
    py_files = filter_py(changed)
    rc = run_mypy(py_files, ns.strict)
    return rc

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
