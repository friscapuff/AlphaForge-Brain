from __future__ import annotations

"""NVDA 5-Year Static Dataset Ingestion & Normalization.

Implements Group 1 (T001–T013) foundation tasks:
 - Data directory convention (expects ./data/NVDA_5y.csv unless overridden)
 - Dataset registry & cached metadata
 - Strict CSV load with dtype coercion
 - Timestamp parsing with assumed America/New_York -> UTC normalization
 - Ascending order enforcement & duplicate drop
 - Missing field drop
 - Zero-volume flag retention
 - Future-dated row exclusion
 - Calendar gap classification (expected closures vs unexpected gaps)
 - Canonical dataset hashing (stable serialization)
 - DatasetMetadata persistence (JSON cache)
 - Pure slicing function (epoch ms boundaries) without mutating canonical frame

NOTE: Integration with orchestrator / run hashing performed in later task groups.
"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import timezone
from pathlib import Path
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

DATA_DIR_DEFAULT = Path("data")
DATA_FILE_NAME = "NVDA_5y.csv"  # Transitional until G04 full generic ingestion
SYMBOL = "NVDA"  # Placeholder constant; will be removed when registry-driven generic loader added
TIMEFRAME = "1d"
CALENDAR_ID = "NASDAQ"  # Nominal label; exchange-calendars uses XNAS or XNYS; choose XNAS equivalent schedule.
EXCHANGE_CALENDAR = "XNYS"  # Using NYSE calendar for session schedule (close enough for illustration)

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


@dataclass(slots=True)
class DatasetMetadata:
    symbol: str
    timeframe: str
    data_hash: str
    calendar_id: str
    row_count_raw: int
    row_count_canonical: int
    first_ts: int
    last_ts: int
    anomaly_counters: Dict[str, int]
    created_at: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)


_DATASET_CACHE: dict[str, Tuple[pd.DataFrame, DatasetMetadata]] = {}
_CACHE_DIR = Path(".cache/datasets")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Support alternate vendor format with headers: Date,Close/Last,Volume,Open,High,Low where prices prefixed with $.
    vendor_cols = {c.lower(): c for c in df.columns}
    if "timestamp" not in df.columns and "date" in vendor_cols:
        # Transform format
        def _clean_price(v: str) -> float:
            if isinstance(v, str):
                v = v.strip().replace("$", "")
            try:
                return float(v)
            except Exception:  # pragma: no cover - defensive
                return float("nan")
        date_col = vendor_cols["date"]
        close_col = vendor_cols.get("close/last") or vendor_cols.get("close")
        open_col = vendor_cols.get("open")
        high_col = vendor_cols.get("high")
        low_col = vendor_cols.get("low")
        vol_col = vendor_cols.get("volume")
        if not all([date_col, close_col, open_col, high_col, low_col, vol_col]):
            raise ValueError("Unrecognized NVDA CSV format; missing required vendor columns")
        transformed = pd.DataFrame()
        transformed["timestamp"] = df[date_col]
        transformed["open"] = df[open_col].map(_clean_price)
        transformed["high"] = df[high_col].map(_clean_price)
        transformed["low"] = df[low_col].map(_clean_price)
        transformed["close"] = df[close_col].map(_clean_price)
        transformed["volume"] = pd.to_numeric(df[vol_col], errors="coerce")
        df = transformed
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df


def _parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    # Assume America/New_York (NY) then convert to UTC epoch ms
    eastern = ZoneInfo("America/New_York")
    # Parse then localize assuming naive timestamps are in Eastern, convert to UTC
    parsed = pd.to_datetime(df["timestamp"], utc=False)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(eastern)
    ts = parsed.dt.tz_convert(timezone.utc)
    df = df.copy()
    df["ts"] = (ts.view("int64") // 1_000_000).astype("int64")  # ns -> ms
    return df


def _classify_calendar_gaps(canonical: pd.DataFrame) -> tuple[int, int]:
    """Return (expected_closures, unexpected_gaps) counts.

    expected closures = number of non-trading days between first & last date (weekends + holidays).
    unexpected gaps = trading sessions present in calendar schedule but missing from dataset.
    """
    if canonical.empty:
        return 0, 0
    cal = xcals.get_calendar(EXCHANGE_CALENDAR)
    # Convert to UTC then drop tz to satisfy exchange_calendars naive requirement
    utc_series = pd.to_datetime(canonical["ts"], unit="ms", utc=True).dt.tz_convert(None)
    first = utc_series.iloc[0].normalize()
    last = utc_series.iloc[-1].normalize()
    schedule = cal.sessions_in_range(first, last)  # schedule is DatetimeIndex (naive)
    dataset_days = set(ts.normalize() for ts in utc_series)  # set of naive dates
    missing_sessions = [s for s in schedule if s.normalize() not in dataset_days]
    # Expected closures = total calendar days in span minus trading sessions
    total_days = (last - first).days + 1
    expected_closures = total_days - len(schedule)
    unexpected_gaps = len(missing_sessions)
    return expected_closures, unexpected_gaps


def _stable_dataframe_hash(df: pd.DataFrame) -> str:
    # Use only canonical columns for hash; ensure sorted by ts
    core = df[["ts", "open", "high", "low", "close", "volume", "zero_volume"]].copy()
    core.sort_values("ts", inplace=True)
    # Deterministic CSV bytes (float precision limited for stability)
    csv_bytes = core.to_csv(index=False, lineterminator="\n", float_format="%.8f").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def _persist_metadata(meta: DatasetMetadata) -> None:
    path = _CACHE_DIR / f"{meta.symbol.lower()}_{meta.data_hash[:12]}.json"
    path.write_text(meta.to_json(), encoding="utf-8")


def load_canonical_dataset(data_dir: Path | None = None) -> tuple[pd.DataFrame, DatasetMetadata]:
    """Load (or return cached) canonical NVDA dataset with normalization + metadata.

    Parameters
    ----------
    data_dir : Path | None
        Root directory containing NVDA_5y.csv. Defaults to ./data.
    """
    if SYMBOL in _DATASET_CACHE:
        return _DATASET_CACHE[SYMBOL]

    root = data_dir or DATA_DIR_DEFAULT
    csv_path = root / DATA_FILE_NAME
    if not csv_path.exists():  # pragma: no cover - developer guidance
        raise FileNotFoundError(f"Expected dataset file not found: {csv_path}")

    raw = _read_csv(csv_path)
    row_count_raw = len(raw)

    # Parse timestamps & add ts
    df = _parse_timestamps(raw)

    # Sort ascending ts
    df = df.sort_values("ts", kind="mergesort").reset_index(drop=True)

    # Drop duplicate timestamps retaining first
    before_dupes = len(df)
    df = df[~df["ts"].duplicated(keep="first")].copy()
    duplicates_dropped = before_dupes - len(df)

    # Drop rows with missing critical fields
    critical = ["open", "high", "low", "close", "volume"]
    before_missing = len(df)
    df = df.dropna(subset=critical)
    rows_dropped_missing = before_missing - len(df)

    # Zero volume flag (retain)
    df["zero_volume"] = (df["volume"] == 0).astype("int8")
    zero_volume_rows = int(df["zero_volume"].sum())

    # Future-dated filter (strictly greater than now UTC)
    now_ms = int(time.time() * 1000)
    before_future = len(df)
    df = df[df["ts"] <= now_ms]
    future_rows_dropped = before_future - len(df)

    # Calendar gap classification
    expected_closures, unexpected_gaps = _classify_calendar_gaps(df)

    # Final canonical column ordering
    canonical_cols = ["ts", "open", "high", "low", "close", "volume", "zero_volume"]
    canonical = df[canonical_cols].copy()

    data_hash = _stable_dataframe_hash(canonical)

    anomaly_counters: Dict[str, int] = {
        "duplicates_dropped": duplicates_dropped,
        "rows_dropped_missing": rows_dropped_missing,
        "zero_volume_rows": zero_volume_rows,
        "future_rows_dropped": future_rows_dropped,
        "unexpected_gaps": unexpected_gaps,
        "expected_closures": expected_closures,
    }

    meta = DatasetMetadata(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        data_hash=data_hash,
        calendar_id=CALENDAR_ID,
        row_count_raw=row_count_raw,
        row_count_canonical=len(canonical),
        first_ts=int(canonical["ts"].iloc[0]) if not canonical.empty else 0,
        last_ts=int(canonical["ts"].iloc[-1]) if not canonical.empty else 0,
        anomaly_counters=anomaly_counters,
        created_at=int(time.time() * 1000),
    )

    _DATASET_CACHE[SYMBOL] = (canonical, meta)
    _persist_metadata(meta)
    return canonical, meta


def get_dataset_metadata() -> DatasetMetadata:
    if SYMBOL not in _DATASET_CACHE:
        load_canonical_dataset()
    return _DATASET_CACHE[SYMBOL][1]


def slice_canonical(start_ms: int | None, end_ms: int | None) -> pd.DataFrame:
    """Return an immutable slice view of the canonical dataset.

    Parameters
    ----------
    start_ms, end_ms : int | None
        Inclusive (start) / inclusive (end) epoch ms boundaries. None leaves boundary open.
    """
    canonical, _ = load_canonical_dataset()
    mask = pd.Series(True, index=canonical.index)
    if start_ms is not None:
        mask &= canonical["ts"] >= start_ms
    if end_ms is not None:
        mask &= canonical["ts"] <= end_ms
    # Return a copy to avoid accidental external mutation
    return canonical.loc[mask].copy().reset_index(drop=True)


def load_dataset_for(symbol: str, timeframe: str, data_dir: Path | None = None) -> tuple[pd.DataFrame, DatasetMetadata]:
    """Generic facade (Phase J G04 prep). Currently only supports NVDA/1d; routes to existing loader.

    Once generic CSV logic is implemented this will dispatch by (symbol,timeframe,provider).
    """
    if symbol.upper() != SYMBOL or timeframe != TIMEFRAME:
        raise NotImplementedError("Generic dataset loading not yet implemented for symbol/timeframe combination.")
    return load_canonical_dataset(data_dir)


def slice_dataset(symbol: str, timeframe: str, start_ms: int | None, end_ms: int | None) -> pd.DataFrame:
    if symbol.upper() != SYMBOL or timeframe != TIMEFRAME:
        raise NotImplementedError("Generic dataset slicing not yet implemented for symbol/timeframe combination.")
    return slice_canonical(start_ms, end_ms)


__all__ = [
    "DatasetMetadata",
    "get_dataset_metadata",
    "load_canonical_dataset",
    "slice_canonical",
    "load_dataset_for",
    "slice_dataset",
]
