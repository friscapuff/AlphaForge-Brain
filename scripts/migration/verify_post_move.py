"""Verify post-move deterministic parity vs baseline.

Reads zz_artifacts/migration_baseline.json and produces
zz_artifacts/migration_verification.json with comparison results.

Checks:
- git head (advisory)
- run_hash equality (if both non-null)
- per-file digest equality for persisted files that still exist
- identifies removed / added / changed files

Exit non-zero if any digest mismatch (excluding allowed_ignored patterns) or run_hash mismatch.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "zz_artifacts"
BASELINE_PATH = ARTIFACTS_DIR / "migration_baseline.json"
OUT_PATH = ARTIFACTS_DIR / "migration_verification.json"

ALLOWED_REMOVED_PATTERNS = [
    r"^src/",  # expected removal after migration
    r"^tests/",  # expected removal after migration
]

TRACK_NEW_PATHS = [
    "alphaforge-brain/src",
    "alphaforge-brain/tests",
    "pyproject.toml",
    "mypy.ini",
    "pytest.ini",
    "ruff.toml",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(base: Path):
    if base.is_file():
        yield base
    else:
        for p in base.rglob("*"):
            if p.is_file():
                yield p


def digest_map(paths: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel in paths:
        p = ROOT / rel
        if not p.exists():
            continue
        for f in iter_files(p):
            rel_key = f.relative_to(ROOT).as_posix()
            result[rel_key] = sha256_file(f)
    return dict(sorted(result.items()))


def matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def main() -> int:
    if not BASELINE_PATH.exists():
        print("[verify] missing baseline file", file=sys.stderr)
        return 2
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_digests: dict[str, str] = baseline.get("file_digests", {})  # type: ignore[assignment]
    current_digests = digest_map(TRACK_NEW_PATHS)

    removed = [k for k in baseline_digests if k not in current_digests]
    added = [k for k in current_digests if k not in baseline_digests]
    changed = [
        k
        for k in baseline_digests
        if k in current_digests and baseline_digests[k] != current_digests[k]
    ]

    # Determine actionable mismatches (exclude expected structural removals)
    unexpected_removed = [
        r for r in removed if not matches_any(ALLOWED_REMOVED_PATTERNS, r)
    ]

    run_hash_ok = True
    run_hash_reason = "skipped (null)"
    if baseline.get("run_hash") is not None:
        # Try to recompute run hash via import if possible
        try:
            from alphaforge_brain import run_hash as rh  # type: ignore

            new_run_hash = (
                str(rh.get_run_hash()) if hasattr(rh, "get_run_hash") else None
            )
        except Exception:
            new_run_hash = None
        if new_run_hash is None:
            run_hash_ok = False
            run_hash_reason = "post-move hash missing"
        else:
            run_hash_ok = new_run_hash == baseline["run_hash"]
            run_hash_reason = f"baseline={baseline['run_hash']} new={new_run_hash}"  # type: ignore[index]

    verdict = {
        "removed": removed,
        "added": added,
        "changed": changed,
        "unexpected_removed": unexpected_removed,
        "run_hash_ok": run_hash_ok,
        "run_hash_detail": run_hash_reason,
    }

    OUT_PATH.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(
        f"[verify] wrote {OUT_PATH.relative_to(ROOT)} | removed={len(removed)} added={len(added)} changed={len(changed)} run_hash_ok={run_hash_ok}"
    )

    # Fail conditions
    if unexpected_removed:
        print("[verify] unexpected removed files detected", file=sys.stderr)
        return 3
    if changed:
        print("[verify] content changes detected vs baseline", file=sys.stderr)
        return 4
    if not run_hash_ok:
        print(f"[verify] run hash mismatch: {run_hash_reason}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
