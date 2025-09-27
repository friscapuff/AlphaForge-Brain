from __future__ import annotations

"""Diagnostic CLI for cache health & parquet capability.

Usage:
  python -m infra.cache.doctor --root <cache_root>

Outputs a JSON document with fields:
  parquet_available: bool
  pyarrow_version: str | null
  metrics: {hits, misses, rebuilds, writes}
  files: list of {path, size, kind}
    kind: parquet | csv_fallback | unknown
"""

from dataclasses import dataclass, asdict
import argparse
import json
from pathlib import Path
from typing import Iterable

from .metrics import cache_metrics
from ._parquet import parquet_available, load_pyarrow


@dataclass
class FileInfo:
    path: str
    size: int
    kind: str


def _classify(path: Path) -> str:
    # Heuristic: if parquet available attempt a light read of first bytes for magic number
    try:
        with open(path, "rb") as f:
            head = f.read(4)
        if head == b"PAR1":  # parquet magic
            return "parquet"
    except Exception:
        return "unknown"
    # If extension is .parquet but magic missing treat as csv fallback
    if path.suffix == ".parquet":
        return "csv_fallback"
    if path.suffix == ".csv":  # explicit csv (not typical in current implementation)
        return "csv_fallback"
    return "unknown"


def _iter_cache_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


def main() -> int:  # pragma: no cover - CLI thin wrapper
    parser = argparse.ArgumentParser(description="Cache diagnostic tool")
    parser.add_argument(
        "--root", type=Path, default=Path(".cache"), help="Cache root directory"
    )
    args = parser.parse_args()
    root: Path = args.root

    pa_mod = load_pyarrow()
    pa_version = getattr(pa_mod, "__version__", None) if pa_mod else None
    avail = parquet_available()

    files: list[FileInfo] = []
    for path in _iter_cache_files(root):
        try:
            size = path.stat().st_size
        except Exception:
            size = -1
        kind = _classify(path)
        files.append(FileInfo(path=str(path), size=size, kind=kind))

    report = {
        "parquet_available": avail,
        "pyarrow_version": pa_version,
        "metrics": cache_metrics.get().snapshot(),
        "files": [asdict(f) for f in files],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

__all__ = ["main"]
