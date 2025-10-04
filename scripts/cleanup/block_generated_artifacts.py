"""
Pre-commit hook: fail if generated artifacts are staged for commit.

Checks the staged file list and blocks known transient artifacts such as
coverage.xml, typing timing files, mypy diff/baseline outputs, and base-/head- prefixed temp files.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


BLOCK_PATTERNS = [
    re.compile(r"^coverage\.xml$"),
    re.compile(r"^typing_timing\.json$"),
    re.compile(r"^typing_timing\.md$"),
    re.compile(r"^mypy_baseline\.txt$"),
    re.compile(r"^mypy_final\.txt$"),
    re.compile(r"^mypy_diff\.md$"),
    re.compile(r"^diff_test\.md$"),
    re.compile(r"^virt_report\.json$"),
    re.compile(r"^base-.*\.yaml$"),
    re.compile(r"^head-.*\.json$"),
]


def get_staged_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=ROOT,
            text=True,
        )
    except Exception:
        return []
    files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
    return files


def is_blocked(path: Path) -> bool:
    name = path.name
    for pat in BLOCK_PATTERNS:
        if pat.match(name):
            return True
    return False


def main() -> int:
    blocked = [p for p in get_staged_files() if is_blocked(p)]
    if blocked:
        print("Refusing to commit generated artifacts:")
        for p in blocked:
            print(f" - {p}")
        print(
            "Remove these files or move them under artifacts/ or zz_artifacts/ if needed."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
