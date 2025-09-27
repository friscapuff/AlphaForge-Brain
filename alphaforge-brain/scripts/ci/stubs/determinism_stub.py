from __future__ import annotations

"""
Determinism CI stub (T002) — placeholder to wire job now and fail later when
backed by real implementation. Exits 0 and prints a TODO JSON summary.

This script will be replaced by a proper determinism replay harness (FR-101/110)
that executes N identical runs and asserts stable run/artifact hashes.
"""

import json
from pathlib import Path
import sys


def main(out: str | None = None) -> int:
    summary = {
        "status": "STUB",
        "todo": "Implement determinism replay and hashing checks",
        "variants": 0,
        "identical": True,
    }
    payload = json.dumps(summary, indent=2)
    if out:
        Path(out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(main(out_path))
