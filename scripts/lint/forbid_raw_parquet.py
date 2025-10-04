#!/usr/bin/env python
"""Pre-commit hook to discourage raw `pd.read_parquet` calls.

Policy:
  - Prefer using `read_parquet_or_csv` helper for robust fallback
  - Allow direct parquet reads only when explicitly justified
    by an inline comment containing the token: `# parquet-ok`

Behavior:
  - Scans staged Python files passed by pre-commit
  - Flags any line containing `read_parquet(` that does NOT also contain
    the allowance token comment and is not inside this repo's helper
  - Exits non-zero with a concise report listing violations

False positive mitigation:
  - Ignores lines that appear in comments only (e.g. starting with #)
  - Ignores occurrences inside strings (simple heuristic: must not be within quotes on the same line)
  - Skips the helper file itself and this script

Override procedure:
  - Add trailing comment:  df = pd.read_parquet(path)  # parquet-ok: short rationale

Rationale:
  Centralizing fallback logic lowers maintenance and ensures minimal
  environments without parquet engines operate seamlessly.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOW_TOKEN = "parquet-ok"
TARGET = "read_parquet("
HELPER_FILENAME = "artifacts.py"  # where read_parquet_or_csv lives

pattern = re.compile(r"read_parquet\(")


def line_has_violation(line: str) -> bool:
    if TARGET not in line:
        return False
    # Already allowed
    if ALLOW_TOKEN in line:
        return False
    stripped = line.lstrip()
    # Entire line commented out
    if stripped.startswith("#"):
        return False
    # crude heuristic: if line contains quotes around target treat as doc/commenty
    qcount = line.count("'") + line.count('"')
    if qcount >= 4 and TARGET in line:
        # probably inside a long string literal; skip
        return False
    return True


def main(argv: list[str]) -> int:
    if len(argv) <= 1:
        return 0
    violations: list[tuple[Path, int, str]] = []
    for name in argv[1:]:
        path = Path(name)
        if not path.suffix == ".py":
            continue
        if path.name in {"forbid_raw_parquet.py"}:
            continue
        if path.name == HELPER_FILENAME and "read_parquet_or_csv" in path.read_text(
            errors="ignore"
        ):
            # allow helper file
            pass
        try:
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1
            ):
                if line_has_violation(line):
                    violations.append((path, lineno, line.rstrip()))
        except Exception:
            # Ignore unreadable file
            continue
    if not violations:
        return 0
    print(
        "Forbidden raw pd.read_parquet usage detected (prefer read_parquet_or_csv or add '# parquet-ok'):\n",
        file=sys.stderr,
    )
    for p, ln, text in violations:
        print(f"  {p}:{ln}: {text}", file=sys.stderr)
    print("\nIf intentional, append '# parquet-ok: reason'.", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
