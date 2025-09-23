"""High-level artifact helpers (FR-014, FR-015, FR-023, FR-024).

This module wraps lower-level domain.artifacts.writer functionality and adds:
- equity & trades parquet writers (placeholders if pandas frames provided)
- deterministic hashing of produced files
- convenience function to assemble artifact index for API layer

It does NOT duplicate manifest hashing logic (delegated to domain.artifacts.writer.write_artifacts).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from lib.hash_utils import file_sha256

ARTIFACT_DIR = Path("artifacts")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    # Deterministic parquet: exclude pandas metadata randomness where possible
    df.to_parquet(path, index=False)


def write_equity(run_hash: str, equity_df: pd.DataFrame, *, base_dir: Path | None = None) -> Path:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    ensure_dir(run_dir)
    path = run_dir / "equity.parquet"
    write_parquet(equity_df, path)
    return path


def write_trades(run_hash: str, trades_df: pd.DataFrame, *, base_dir: Path | None = None) -> Path:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    ensure_dir(run_dir)
    path = run_dir / "trades.parquet"
    write_parquet(trades_df, path)
    return path


def write_json(run_hash: str, name: str, obj: Any, *, base_dir: Path | None = None) -> Path:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    ensure_dir(run_dir)
    path = run_dir / name
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return path


def artifact_index(run_hash: str, extra: Iterable[str] | None = None, *, base_dir: Path | None = None) -> list[dict[str, Any]]:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    if not run_dir.exists():
        return []
    # Exclude manifest.json itself; index is for content artifacts
    allowed = {"summary.json","metrics.json","validation.json","validation_detail.json","equity.parquet","trades.parquet","plots.png"}
    if extra:
        allowed.update(extra)
    items: list[dict[str, Any]] = []
    for p in sorted(run_dir.iterdir()):
        if p.name not in allowed or not p.is_file():
            continue
        try:
            items.append({"name": p.name, "sha256": file_sha256(p), "size": p.stat().st_size})
        except Exception:  # pragma: no cover - skip unreadable
            continue
    return items

__all__ = ["ARTIFACT_DIR", "artifact_index", "write_equity", "write_json", "write_trades"]
