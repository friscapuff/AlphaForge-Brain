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

from infra.cache._parquet import log_csv_fallback_once, parquet_available

ARTIFACT_DIR = Path("artifacts")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame as parquet if available, else CSV under .parquet name.

    Mirrors cache fallback semantics so artifact tests don't fail in environments
    lacking a working parquet engine (e.g. pyarrow binary mismatch). A one-time
    structured log is emitted the first time we degrade to CSV.
    """
    if parquet_available():
        try:
            df.to_parquet(path, index=False)
            return
        except Exception:  # pragma: no cover - engine present but runtime failure
            log_csv_fallback_once("artifact_pyarrow_write_failed")
    else:
        log_csv_fallback_once("artifact_pyarrow_unavailable")
    # Fallback: write CSV bytes with parquet extension
    path.write_text(df.to_csv(index=False), encoding="utf-8")


def write_equity(
    run_hash: str, equity_df: pd.DataFrame, *, base_dir: Path | None = None
) -> Path:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    ensure_dir(run_dir)
    path = run_dir / "equity.parquet"
    write_parquet(equity_df, path)
    return path


def write_trades(
    run_hash: str, trades_df: pd.DataFrame, *, base_dir: Path | None = None
) -> Path:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    ensure_dir(run_dir)
    path = run_dir / "trades.parquet"
    write_parquet(trades_df, path)
    return path


def write_json(
    run_hash: str, name: str, obj: Any, *, base_dir: Path | None = None
) -> Path:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    ensure_dir(run_dir)
    path = run_dir / name
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return path


def artifact_index(
    run_hash: str, extra: Iterable[str] | None = None, *, base_dir: Path | None = None
) -> list[dict[str, Any]]:
    run_dir = (base_dir or ARTIFACT_DIR) / run_hash
    if not run_dir.exists():
        return []
    # Exclude manifest.json itself; index is for content artifacts
    allowed = {
        "summary.json",
        "metrics.json",
        "validation.json",
        "validation_detail.json",
        "equity.parquet",
        "trades.parquet",
        "plots.png",
    }
    if extra:
        allowed.update(extra)
    items: list[dict[str, Any]] = []
    for p in sorted(run_dir.iterdir()):
        if p.name == ".evicted":
            continue  # hidden demoted storage
        if p.name not in allowed or not p.is_file():
            continue
        try:
            items.append(
                {"name": p.name, "sha256": file_sha256(p), "size": p.stat().st_size}
            )
        except Exception:  # pragma: no cover - skip unreadable
            continue
    return items


def read_parquet_or_csv(path: Path) -> pd.DataFrame:
    """Best-effort read of a DataFrame stored as parquet or CSV-under-parquet.

    Attempts pandas.read_parquet first; if the environment lacks a parquet engine or
    the file actually contains CSV bytes (our fallback write mode), fall back to
    pandas.read_csv. Raises the final exception only if both attempts fail.
    """
    try:
        return pd.read_parquet(  # parquet-ok: direct artifact read acceptable in controlled test env 
            path
        )  # parquet-ok: primary attempt; helper provides fallback
    except Exception:
        # Fall back to CSV (expected in minimal envs without pyarrow/fastparquet)
        return pd.read_csv(path)


__all__ = [
    "ARTIFACT_DIR",
    "artifact_index",
    "write_equity",
    "write_json",
    "write_trades",
    "read_parquet_or_csv",
]
