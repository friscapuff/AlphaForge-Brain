#!/usr/bin/env python
"""Compare two mypy snapshot JSON files and emit a markdown diff report.

Usage:
  poetry run python scripts/typing/diff_mypy.py --base base.json --new new.json --out report.md

Exit codes:
  0 if no regressions.
  1 if new errors introduced or error count increased.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_snapshot(p: Path) -> dict[str, Any]:
    if not p.exists():
        return {"error_count": 0, "errors": []}
    raw: Any = json.loads(p.read_text(encoding="utf-8"))
    # Snapshot JSON schema: {error_count: int, errors: list[dict[str, Any]]}
    if not isinstance(raw, dict):  # pragma: no cover - defensive
        return {"error_count": 0, "errors": []}
    return raw


def index_errors(errors: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    idx: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for e in errors:
        key = (e["path"], e["line"], e["col"], e["type"])
        idx[key] = e
    return idx


def diff(base: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    base_idx = index_errors(base.get("errors", []))
    new_idx = index_errors(new.get("errors", []))
    added_keys = [k for k in new_idx.keys() if k not in base_idx]
    removed_keys = [k for k in base_idx.keys() if k not in new_idx]
    return {
        "base_count": base.get("error_count", 0),
        "new_count": new.get("error_count", 0),
        "added": [new_idx[k] for k in sorted(added_keys)],
        "removed": [base_idx[k] for k in sorted(removed_keys)],
    }


def format_md(d: dict[str, Any]) -> str:
    lines = ["# Mypy Diff Report",""]
    lines.append(f"Base errors: {d['base_count']}  New errors: {d['new_count']}")
    delta = d["new_count"] - d["base_count"]
    lines.append(f"Delta: {delta:+d}")
    lines.append("")
    if d["added"]:
        lines.append("## Added Errors")
        for e in d["added"]:
            lines.append(f"- {e['path']}:{e['line']}:{e['col']} {e['type']}: {e['message']}")
    if d["removed"]:
        lines.append("## Resolved Errors")
        for e in d["removed"]:
            lines.append(f"- {e['path']}:{e['line']}:{e['col']} {e['type']}: {e['message']}")
    if not d["added"] and not d["removed"]:
        lines.append("No changes in mypy error set.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    base = load_snapshot(Path(ns.base))
    new = load_snapshot(Path(ns.new))
    d = diff(base, new)
    md = format_md(d)
    Path(ns.out).write_text(md + "\n", encoding="utf-8")
    print(md)
    # regression if new_count > base_count
    if d["new_count"] > d["base_count"]:
        return 1
    return 0

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
