#!/usr/bin/env python
"""Fail CI if constitution changed without CHANGELOG entry.

Heuristic:
- If diff includes .specify/memory/constitution.md
- And CHANGELOG.md does NOT contain current constitution version string from file
  => fail with error instructing to add entry.

Assumes constitution file contains line: **Version**: X.Y.Z |
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

CONSTITUTION_PATH = Path('.specify/memory/constitution.md')
CHANGELOG_PATH = Path('CHANGELOG.md')

VERSION_PATTERN = re.compile(r"\*\*Version\*\*:\s*(?P<ver>\d+\.\d+\.\d+)")


def get_current_version() -> str:
    text = CONSTITUTION_PATH.read_text(encoding='utf-8')
    m = VERSION_PATTERN.search(text)
    if not m:
        print("ERROR: Unable to locate constitution version line.", file=sys.stderr)
        sys.exit(2)
    return m.group('ver')


def constitution_changed() -> bool:
    try:
        diff = subprocess.check_output(['git', 'diff', '--name-only', 'origin/main...HEAD'], text=True)
    except subprocess.CalledProcessError as e:
        print(f"WARN: git diff failed ({e}); assuming no change.")
        return False
    return any(line.strip() == str(CONSTITUTION_PATH) for line in diff.splitlines())


def changelog_contains(version: str) -> bool:
    if not CHANGELOG_PATH.exists():
        return False
    text = CHANGELOG_PATH.read_text(encoding='utf-8')
    return version in text


def main() -> None:
    if not CONSTITUTION_PATH.exists():
        print("No constitution present; skipping enforcement.")
        return
    if not constitution_changed():
        print("Constitution not changed in this diff; OK")
        return
    ver = get_current_version()
    if changelog_contains(ver):
        print(f"Constitution change detected; CHANGELOG contains version {ver}; OK")
        return
    print(
        f"ERROR: Constitution modified but CHANGELOG missing entry for version {ver}.\n"
        f"Add an Added/Changed section referencing principles or governance updates.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == '__main__':
    main()
