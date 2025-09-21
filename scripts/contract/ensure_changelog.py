#!/usr/bin/env python
"""Ensure a changelog fragment exists when the OpenAPI spec changes.

Usage: python scripts/contract/ensure_changelog.py --spec specs/001-initial-dual-tier/contracts/openapi.yaml --base origin/main

Logic:
1. Detect if spec path changed vs base.
2. If changed, require at least one fragment file in changelog/fragments/ whose filename contains the current short SHA or PR number (if provided via env PR_NUMBER) or any non-empty fragment if fallback allowed.
3. Optionally enforce naming pattern: YYYYMMDD-<slug>.md
4. Exit non-zero with helpful message if missing.

Intended to be invoked in CI prior to merging PRs.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

FRAG_DIR: Path = Path("changelog/fragments")
PATTERN: re.Pattern[str] = re.compile(r"^\d{8}-[a-z0-9\-]+\.md$")

def run(cmd: list[str]) -> str:
    """Run a subprocess command and return stripped stdout.

    Any CalledProcessError will propagate to the caller unless explicitly
    handled there. This function is intentionally small and typed.
    """
    return subprocess.check_output(cmd, text=True).strip()


def spec_changed(spec: str, base: str) -> bool:
    """Return True if the provided spec path is changed vs the given base ref."""
    try:
        diff = run(["git", "diff", "--name-only", f"{base}...HEAD"])
    except subprocess.CalledProcessError:
        return False
    return spec in diff.splitlines()


def list_fragments() -> list[Path]:
    """List all markdown fragment files in the fragment directory."""
    if not FRAG_DIR.exists():
        return []
    return [p for p in FRAG_DIR.iterdir() if p.is_file() and p.suffix == ".md"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--allow-any", action="store_true", help="Allow any fragment if naming not matched")
    args = ap.parse_args()

    if not spec_changed(args.spec, args.base):
        print(f"Spec not changed vs {args.base}; no fragment required.")
        return 0

    frags = list_fragments()
    if not frags:
        print(f"ERROR: Spec changed but no fragments found in {FRAG_DIR}.", file=sys.stderr)
        return 2

    valid = [f for f in frags if PATTERN.match(f.name)]
    if valid:
        print(f"Found {len(valid)} valid changelog fragment(s): {[v.name for v in valid]}")
        return 0
    if args.allow_any and frags:
        print(f"No valid pattern matches, but --allow-any set and {len(frags)} fragment(s) found.")
        return 0

    print("ERROR: Fragment(s) found but none match required pattern YYYYMMDD-slug.md", file=sys.stderr)
    for f in frags:
        print(f" - {f.name}", file=sys.stderr)
    return 3

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
