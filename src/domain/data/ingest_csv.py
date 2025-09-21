from __future__ import annotations
"""Generic CSV ingestion (Phase J continuation of G04/G05).

Currently supports daily timeframe datasets with required columns and basic normalization.
Multi-symbol capable; integrates with dataset registry entries specifying path & calendar.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple
import time
import hashlib
import pandas as pd
import exchange_calendars as xcals
from zoneinfo import ZoneInfo

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

@dataclass(slots=True)
class GenericDatasetMetadata:
    symbol: str
    timeframe: str
    data_hash: str
    calendar_id: str | None
    row_count_raw: int
    row_count_canonical: int
    first_ts: int
    last_ts: int
    anomaly_counters: Dict[str, int]
    created_at: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()

_DATASET_CACHE: dict[tuple[str,str], Tuple[pd.DataFrame, GenericDatasetMetadata]] = {}
_CACHE_DIR = Path(".cache/datasets")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df

def _parse_timestamps(df: pd.DataFrame, tz: str = "America/New_York") -> pd.DataFrame:
    eastern = ZoneInfo(tz)
    parsed = pd.to_datetime(df["timestamp"], utc=False)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(eastern)
    ts = parsed.dt.tz_convert("UTC")
    out = df.copy()
    out["ts"] = (ts.view("int64") // 1_000_000).astype("int64")
    return out

def _classify_calendar_gaps(canonical: pd.DataFrame, calendar_id: str | None) -> tuple[int,int]:
    if canonical.empty or not calendar_id:
        return 0,0
    cal = xcals.get_calendar(calendar_id)
    utc_series = pd.to_datetime(canonical["ts"], unit="ms", utc=True).dt.tz_convert(None)
    first = utc_series.iloc[0].normalize()
    last = utc_series.iloc[-1].normalize()
    schedule = cal.sessions_in_range(first, last)
    dataset_days = set(ts.normalize() for ts in utc_series)
    missing_sessions = [s for s in schedule if s.normalize() not in dataset_days]
    total_days = (last - first).days + 1
    expected_closures = total_days - len(schedule)
    unexpected_gaps = len(missing_sessions)
    return expected_closures, unexpected_gaps

def _stable_dataframe_hash(df: pd.DataFrame) -> str:
    core = df[["ts","open","high","low","close","volume","zero_volume"]].copy()
    core.sort_values("ts", inplace=True)
    csv_bytes = core.to_csv(index=False, lineterminator="\n", float_format="%.8f").encode()
    return hashlib.sha256(csv_bytes).hexdigest()

def load_generic_csv(symbol: str, timeframe: str, path: Path, calendar_id: str | None) -> tuple[pd.DataFrame, GenericDatasetMetadata]:
    key = (symbol.upper(), timeframe)
    if key in _DATASET_CACHE:
        return _DATASET_CACHE[key]
    raw = _read_csv(path)
    row_count_raw = len(raw)
    df = _parse_timestamps(raw)
    df = df.sort_values("ts", kind="mergesort").reset_index(drop=True)
    before_dupes = len(df)
    df = df[~df["ts"].duplicated(keep="first")].copy()
    duplicates_dropped = before_dupes - len(df)
    critical = ["open","high","low","close","volume"]
    before_missing = len(df)
    df = df.dropna(subset=critical)
    rows_dropped_missing = before_missing - len(df)
    df["zero_volume"] = (df["volume"] == 0).astype("int8")
    zero_volume_rows = int(df["zero_volume"].sum())
    now_ms = int(time.time()*1000)
    before_future = len(df)
    df = df[df["ts"] <= now_ms]
    future_rows_dropped = before_future - len(df)
    expected_closures, unexpected_gaps = _classify_calendar_gaps(df, calendar_id)
    canonical_cols = ["ts","open","high","low","close","volume","zero_volume"]
    canonical = df[canonical_cols].copy()
    data_hash = _stable_dataframe_hash(canonical)
    counters: Dict[str,int] = {
        "duplicates_dropped": duplicates_dropped,
        "rows_dropped_missing": rows_dropped_missing,
        "zero_volume_rows": zero_volume_rows,
        "future_rows_dropped": future_rows_dropped,
        "unexpected_gaps": unexpected_gaps,
        "expected_closures": expected_closures,
    }
    meta = GenericDatasetMetadata(
        symbol=symbol.upper(), timeframe=timeframe, data_hash=data_hash, calendar_id=calendar_id,
        row_count_raw=row_count_raw, row_count_canonical=len(canonical),
        first_ts=int(canonical["ts"].iloc[0]) if not canonical.empty else 0,
        last_ts=int(canonical["ts"].iloc[-1]) if not canonical.empty else 0,
        anomaly_counters=counters, created_at=int(time.time()*1000)
    )
    _DATASET_CACHE[key] = (canonical, meta)
    return canonical, meta

def slice_generic(symbol: str, timeframe: str, start_ms: int | None, end_ms: int | None) -> pd.DataFrame:
    key = (symbol.upper(), timeframe)
    if key not in _DATASET_CACHE:
        raise KeyError("Dataset not loaded; call load_generic_csv first")
    canonical = _DATASET_CACHE[key][0]
    mask = pd.Series(True, index=canonical.index)
    if start_ms is not None:
        mask &= canonical["ts"] >= start_ms
    if end_ms is not None:
        mask &= canonical["ts"] <= end_ms
    return canonical.loc[mask].copy().reset_index(drop=True)

__all__ = [
    "GenericDatasetMetadata","load_generic_csv","slice_generic"
]
