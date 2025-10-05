"""Capture pre-migration deterministic baseline.

Outputs zz_artifacts/migration_baseline.json containing:
- timestamp UTC ISO8601
- git_head (if available)
- run_hash (from pipeline if module available; else null)
- python_version
- platform info
- file_digests: sha256 for tracked paths (source + tests)
- metrics: placeholder for future timing / counts

Exit code 0 on success, non-zero on failure.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "zz_artifacts"
OUT_PATH = ARTIFACTS_DIR / "migration_baseline.json"

TRACK_PATHS = [
    "src",
    "tests",
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


def iter_files(base: Path) -> Iterable[Path]:
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


def get_git_head() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
            .decode()
            .strip()
        )
    except Exception:
        return None


def try_run_hash() -> str | None:
    # Attempt to import a run hash provider if it exists pre-migration.
    candidates = [
        "alphaforge_brain.run_hash",  # hypothetical future location
        "run_hash",  # fallback simple module
    ]
    for mod in candidates:
        try:
            m = __import__(mod, fromlist=["get_run_hash"])
            if hasattr(m, "get_run_hash"):
                return str(
                    m.get_run_hash()
                )  # attribute presence checked via hasattr above
        except Exception:
            continue
    return None


def main() -> int:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    file_digests = digest_map(TRACK_PATHS)
    data: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_head": get_git_head(),
        "python_version": sys.version,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "run_hash": try_run_hash(),
        "file_digests": file_digests,
        "metrics": {},
        "notes": "Baseline prior to dual-root migration.",
    }
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    # data['file_digests'] is a dict[str, str]; extract then measure length for mypy clarity.
    file_digests_val = data["file_digests"]
    if isinstance(file_digests_val, dict):
        count = len(file_digests_val)
    else:  # fallback defensive
        count = 0
    print(f"[baseline] wrote {OUT_PATH.relative_to(ROOT)} with {count} file digests")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
