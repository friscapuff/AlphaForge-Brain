from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from infra.utils.hash import sha256_hex

# Key format components truncated for directory depth safety
_KEY_PREFIX_LEN = 12


def _frame_content_hash(frame: pd.DataFrame) -> str:
    # Use CSV representation for deterministic hashing (no index)
    csv_str: str = frame.to_csv(index=False)  # pandas returns str
    csv_bytes = csv_str.encode("utf-8")
    digest: str = sha256_hex(csv_bytes)
    return digest


def _compose_key(symbol: str, start: int | None, end: int | None, content_hash: str) -> str:
    return f"{symbol}:{start}:{end}:{content_hash[:_KEY_PREFIX_LEN]}"


@dataclass
class CandleCache:
    root: Path
    on_store: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._last_key: str | None = None

    # Public API
    def store(self, *, symbol: str, start: int | None, end: int | None, frame: pd.DataFrame) -> Path:
        content_hash = _frame_content_hash(frame)
        key = _compose_key(symbol, start, end, content_hash)
        self._last_key = key
        path = self._path_for_key(key)
        if path.exists():  # idempotent reuse
            return path
        tmp = path.with_suffix(path.suffix + ".tmp")
        frame.to_parquet(tmp, index=False)  # requires pyarrow
        tmp.replace(path)  # atomic-ish on same filesystem
        if self.on_store:
            self.on_store()
        return path

    def load(self, *, symbol: str, start: int | None, end: int | None, frame: pd.DataFrame) -> pd.DataFrame:
        # Recompute key based on passed frame to ensure identical path
        content_hash = _frame_content_hash(frame)
        key = _compose_key(symbol, start, end, content_hash)
        path = self._path_for_key(key)
        if not path.exists():  # cache miss -> store then load
            self.store(symbol=symbol, start=start, end=end, frame=frame)
        return pd.read_parquet(path)

    # Internal helpers
    def _path_for_key(self, key: str) -> Path:
        # Use first two chars of hash part to shard directories
        parts = key.split(":")
        hash_part = parts[-1]
        shard = hash_part[:2]
        dir_path = self.root / shard
        dir_path.mkdir(exist_ok=True)
        return dir_path / f"{key}.parquet"


__all__ = ["CandleCache"]
