from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from .metrics import cache_metrics


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_KEY_PREFIX_LEN = 12


def _frame_content_hash(frame: pd.DataFrame) -> str:
    csv_text: str = frame.to_csv(index=False)
    digest: str = sha256_hex(csv_text.encode("utf-8"))
    return digest


def _compose_key(
    symbol: str, start: int | None, end: int | None, content_hash: str
) -> str:
    return f"{symbol}:{start}:{end}:{content_hash[:_KEY_PREFIX_LEN]}"


@dataclass
class CandleCache:
    root: Path
    on_store: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._last_key: str | None = None

    def store(
        self, *, symbol: str, start: int | None, end: int | None, frame: pd.DataFrame
    ) -> Path:
        content_hash = _frame_content_hash(frame)
        key = _compose_key(symbol, start, end, content_hash)
        self._last_key = key
        path = self._path_for_key(key)
        if path.exists():
            cache_metrics.record_hit()
            return path
        tmp = path.with_suffix(path.suffix + ".tmp")
        frame.to_parquet(tmp, index=False)
        tmp.replace(path)
        if self.on_store:
            try:  # pragma: no cover - callback robustness
                self.on_store()
            except Exception:
                pass
        cache_metrics.record_write()
        return path

    def load(
        self, *, symbol: str, start: int | None, end: int | None, frame: pd.DataFrame
    ) -> pd.DataFrame:
        content_hash = _frame_content_hash(frame)
        key = _compose_key(symbol, start, end, content_hash)
        path = self._path_for_key(key)
        if not path.exists():
            cache_metrics.record_miss()
            self.store(symbol=symbol, start=start, end=end, frame=frame)
            return pd.read_parquet(path)
        cache_metrics.record_hit()
        return pd.read_parquet(path)

    def _path_for_key(self, key: str) -> Path:
        hash_part = key.split(":")[-1]
        shard = hash_part[:2]
        dir_path = self.root / shard
        dir_path.mkdir(exist_ok=True)
        safe_key = key.replace(":", "_")  # Windows-safe filename
        return dir_path / f"{safe_key}.parquet"


__all__ = ["CandleCache"]
