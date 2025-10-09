#!/usr/bin/env python3
"""Generate Error Code Reference for docs.

Writes a Markdown table under docs/error-codes.md using api.error_codes registry.
Optionally prints to stdout if --stdout is passed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure brain src is importable if running from repo root
ROOT = Path(__file__).resolve().parents[2]
BRAIN_SRC = ROOT / "alphaforge-brain" / "src"
if str(BRAIN_SRC) not in sys.path:
    sys.path.insert(0, str(BRAIN_SRC))

from api.error_codes import render_markdown_table  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default=str(ROOT / "docs" / "error-codes.md"))
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    table = render_markdown_table()
    if args.stdout:
        print(table)
    out_path = Path(args.out)
    out_path.write_text(table, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
