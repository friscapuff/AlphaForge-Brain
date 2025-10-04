#!/usr/bin/env python
"""Fail commit if pyproject.toml changed without poetry.lock.

Logic:
 - Use 'git diff --name-only --cached' to inspect staged files.
 - If pyproject.toml is staged AND poetry.lock is not, fail.
 - If poetry.lock staged alone (rare), allow (lock refresh only).

Rationale: Prevent drift where dependency changes are committed without the
deterministic lockfile update. This keeps CI & local consistent.
"""
from __future__ import annotations

import subprocess
import sys


def staged_paths() -> set[str]:
    out = subprocess.check_output(["git", "diff", "--name-only", "--cached"], text=True)
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def main() -> None:
    paths = staged_paths()
    if "pyproject.toml" in paths and "poetry.lock" not in paths:
        print(
            "[lock-sync] pyproject.toml staged without poetry.lock. Run 'poetry lock' and include lockfile.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print("[lock-sync] OK")


if __name__ == "__main__":  # pragma: no cover
    main()
