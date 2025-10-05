from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd
from lib.artifacts import read_parquet_or_csv

from infra.utils.hash import sha256_hex

from ._parquet import log_csv_fallback_once, parquet_available
from .metrics import cache_metrics

_KEY_PREFIX_LEN = 12


def _frame_content_hash(frame: pd.DataFrame) -> str:
    csv_text: str = frame.to_csv(index=False)
    csv_bytes: bytes = csv_text.encode("utf-8")
    digest: str = sha256_hex(csv_bytes)
    return digest


def _compose_key(
    symbol: str, start: int | None, end: int | None, content_hash: str
) -> str:
    return f"{symbol}:{start}:{end}:{content_hash[:_KEY_PREFIX_LEN]}"


@dataclass
class CandleCache:
    root: Path
    on_store: Callable[[], None] | None = None
    _last_key: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        # Normalize to Path regardless of input type
        root_path: Path = Path(self.root)
        self.root = root_path
        root_path.mkdir(parents=True, exist_ok=True)

    def store(
        self, *, symbol: str, start: int | None, end: int | None, frame: pd.DataFrame
    ) -> Path:
        content_hash = _frame_content_hash(frame)
        key = _compose_key(symbol, start, end, content_hash)
        self._last_key = key
        # Always use .parquet extension for deterministic naming (CSV fallback stored with .parquet if needed)
        path = self._path_for_key(key, ".parquet")
        if path.exists():
            cache_metrics.record_hit()
            return path
        tmp: Path = path.with_suffix(path.suffix + ".tmp")
        if parquet_available():
            try:
                frame.to_parquet(tmp, index=False)
            except Exception:  # pragma: no cover - unexpected runtime issue
                log_csv_fallback_once("pyarrow_write_failed")
                frame.to_csv(tmp, index=False)
        else:  # CSV fallback written with parquet extension
            log_csv_fallback_once("pyarrow_unavailable")
            frame.to_csv(tmp, index=False)
        tmp.replace(path)
        if self.on_store:
            self.on_store()
        cache_metrics.record_write()
        return path

    def load(
        self, *, symbol: str, start: int | None, end: int | None, frame: pd.DataFrame
    ) -> pd.DataFrame:
        content_hash = _frame_content_hash(frame)
        key = _compose_key(symbol, start, end, content_hash)
        parquet_path = self._path_for_key(key, ".parquet")
        if parquet_path.exists():
            cache_metrics.record_hit()
            if parquet_available():
                try:
                    return read_parquet_or_csv(parquet_path)
                except Exception:
                    pass
            # Parquet unavailable or failed -> try explicit CSV read (helper already attempted both)
            df = pd.read_csv(parquet_path)
            # Basic schema sanity (at least timestamp & close)
            if {"timestamp", "close"}.issubset(df.columns):
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                except Exception:
                    pass
                return df
            # If schema invalid treat as miss -> rebuild
            try:
                parquet_path.unlink()
            except Exception:
                pass
        # Miss -> build
        cache_metrics.record_miss()
        stored_path = self.store(symbol=symbol, start=start, end=end, frame=frame)
        # Read back using appropriate loader
        if parquet_available():
            try:
                return read_parquet_or_csv(stored_path)
            except Exception:
                pass
        df2 = pd.read_csv(stored_path)
        if "timestamp" in df2.columns:
            try:
                df2["timestamp"] = pd.to_datetime(df2["timestamp"], utc=True)
            except Exception:
                pass
        return df2

    def _path_for_key(self, key: str, ext: str) -> Path:
        hash_part: str = key.split(":")[-1]
        shard: str = hash_part[:2]
        base: Path = Path(self.root)
        dir_path: Path = base / shard
        dir_path.mkdir(exist_ok=True)
        safe_key: str = key.replace(":", "_")
        return dir_path / f"{safe_key}{ext}"


__all__ = ["CandleCache"]
