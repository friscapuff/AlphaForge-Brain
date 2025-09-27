#!/usr/bin/env python3
"""Generate a mini Table of Contents for README.

Scans README.md for markdown headings (levels 1–3) excluding those after the
TOC END marker and injects bullet list between TOC START/END markers.

Usage:
  python scripts/docs/generate_readme_toc.py [--dry-run]

Outputs modified README in place unless --dry-run.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

README = Path("README.md")
START = "<!-- TOC START"
END = "<!-- TOC END"
HEADING_RE = re.compile(r'^(#{1,3})\s+(.*)')


def slugify(title: str) -> str:
    slug = title.strip().lower()
    # Remove code ticks
    slug = slug.replace('`', '')
    # Replace non alphanum with hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug


def build_toc(lines: list[str]) -> list[str]:
    toc: list[str] = []
    for line in lines:
        if line.startswith(START):
            break
        m = HEADING_RE.match(line)
        if not m:
            continue
        hashes, title = m.groups()
        level = len(hashes)
        if level > 3:
            continue
        anchor = slugify(title)
        indent = '  ' * (level - 1)
        toc.append(f"{indent}- [{title}](#{anchor})")
    return toc


def apply(readme_text: str, toc_block: list[str]) -> str:
    lines = readme_text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith(START):
            inside = True
            out.append(line)
            out.extend(toc_block)
            continue
        if line.startswith(END):
            inside = False
            out.append(line)
            continue
        if inside:
            continue
        out.append(line)
    return '\n'.join(out) + '\n'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    text = README.read_text(encoding='utf-8')
    lines = text.splitlines()
    toc = build_toc(lines)
    new_text = apply(text, toc)
    if args.dry_run:
        print('\n'.join(toc))
        return 0
    README.write_text(new_text, encoding='utf-8')
    print(f"Injected TOC with {len(toc)} entries.")
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
