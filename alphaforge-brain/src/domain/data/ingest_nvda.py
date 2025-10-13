"""NVDA 5-Year Static Dataset Ingestion & Normalization.

Implements Group 1 (T001-T013) foundation tasks:
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

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import SupportsFloat

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

from infra.time.timestamps import to_epoch_ms

from .adjustments import (
    AdjustmentFactors,
    AdjustmentPolicy,
    apply_full_adjustments,
    compute_factors_digest,
    incorporate_policy_into_hash,
)

# G14 modernization: removed legacy typing.Dict / Tuple usage (using builtins)

DATA_DIR_DEFAULT = Path("data")
DATA_FILE_NAME = "NVDA_5y.csv"  # Transitional until G04 full generic ingestion
SYMBOL = "NVDA"  # Placeholder constant; will be removed when registry-driven generic loader added
TIMEFRAME = "1d"
CALENDAR_ID = "NASDAQ"  # Nominal label; exchange-calendars uses XNAS or XNYS; choose XNAS equivalent schedule.
EXCHANGE_CALENDAR = (
    "XNYS"  # Using NYSE calendar for session schedule (close enough for illustration)
)

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
    anomaly_counters: dict[str, int]
    created_at: int
    # Phase K enrichment (initial fields; will be optional backfilled)
    observed_bar_seconds: int | None = None
    declared_bar_seconds: int | None = None
    timeframe_ok: bool | None = None
    # FR-104 additions
    adjustment_policy: str | None = None
    adjustment_factors_digest: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)


_DATASET_CACHE: dict[tuple[str, str, str], tuple[pd.DataFrame, DatasetMetadata]] = {}
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
            raise ValueError(
                "Unrecognized NVDA CSV format; missing required vendor columns"
            )
        transformed = pd.DataFrame()
        timestamp_series = pd.to_datetime(
            df[date_col], errors="coerce", format="%m/%d/%Y"
        )
        transformed["timestamp"] = timestamp_series.dt.strftime("%Y-%m-%d")
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
    out = df.copy()
    out["ts"] = to_epoch_ms(out["timestamp"], assume_tz="America/New_York")
    return out


def _classify_calendar_gaps(canonical: pd.DataFrame) -> tuple[int, int]:
    """Return (expected_closures, unexpected_gaps) counts.

    expected closures = number of non-trading days between first & last date (weekends + holidays).
    unexpected gaps = trading sessions present in calendar schedule but missing from dataset.
    """
    if canonical.empty:
        return 0, 0
    cal = xcals.get_calendar(EXCHANGE_CALENDAR)
    # Convert to UTC then drop tz to satisfy exchange_calendars naive requirement
    utc_series = pd.to_datetime(canonical["ts"], unit="ms", utc=True).dt.tz_convert(
        None
    )
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


def _stable_dataframe_hash(records: list[dict[str, float | int]]) -> str:
    header = "ts,open,high,low,close,volume,zero_volume"
    lines = [header]
    for rec in sorted(records, key=lambda item: item["ts"]):
        lines.append(
            f"{int(rec['ts'])},{rec['open']:.8f},{rec['high']:.8f},{rec['low']:.8f},{rec['close']:.8f},{rec['volume']:.8f},{int(rec['zero_volume'])}"
        )
    csv_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def _persist_metadata(meta: DatasetMetadata) -> None:
    path = _CACHE_DIR / f"{meta.symbol.lower()}_{meta.data_hash[:12]}.json"
    path.write_text(meta.to_json(), encoding="utf-8")


def load_canonical_dataset(
    data_dir: Path | None = None,
    *,
    adjustment_policy: AdjustmentPolicy = "none",
    adjustment_factors: AdjustmentFactors | None = None,
) -> tuple[pd.DataFrame, DatasetMetadata]:
    """Load (or return cached) canonical NVDA dataset with normalization + metadata.

    Parameters
    ----------
    data_dir : Path | None
        Root directory containing NVDA_5y.csv. Defaults to ./data.
    """
    # Compute factors digest early to build cache key
    factors_digest_key = (
        compute_factors_digest(adjustment_policy, adjustment_factors)
        if adjustment_policy == "full_adjusted"
        else None
    )
    cache_key = (SYMBOL, adjustment_policy, factors_digest_key or "none")
    if cache_key in _DATASET_CACHE:
        return _DATASET_CACHE[cache_key]

    root = data_dir or DATA_DIR_DEFAULT
    csv_path = root / DATA_FILE_NAME
    if not csv_path.exists():  # pragma: no cover - developer guidance
        raise FileNotFoundError(f"Expected dataset file not found: {csv_path}")

    raw = _read_csv(csv_path)
    row_count_raw = len(raw)

    records = raw.to_dict("records")
    prepared: list[dict[str, float | int]] = []
    duplicates_dropped = 0
    rows_dropped_missing = 0
    zero_volume_rows = 0
    future_rows_dropped = 0
    seen_ts: set[int] = set()
    now_ms = int(time.time() * 1000)
    assume_zone = ZoneInfo("America/New_York")

    def _as_float(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return float(stripped)
            except ValueError:
                return None
        if isinstance(value, SupportsFloat):
            return float(value)
        return None

    for rec in records:
        timestamp_raw = rec.get("timestamp")
        if timestamp_raw is None or (
            isinstance(timestamp_raw, float) and math.isnan(timestamp_raw)
        ):
            rows_dropped_missing += 1
            continue
        try:
            ts_local = datetime.fromisoformat(str(timestamp_raw))
        except Exception:
            rows_dropped_missing += 1
            continue
        if ts_local.tzinfo is None:
            ts_local = ts_local.replace(tzinfo=assume_zone)
        ts_ms = int(ts_local.astimezone(ZoneInfo("UTC")).timestamp() * 1000)

        open_val = _as_float(rec.get("open"))
        high_val = _as_float(rec.get("high"))
        low_val = _as_float(rec.get("low"))
        close_val = _as_float(rec.get("close"))
        volume_val = _as_float(rec.get("volume"))
        if (
            open_val is None
            or high_val is None
            or low_val is None
            or close_val is None
            or volume_val is None
        ):
            rows_dropped_missing += 1
            continue
        if any(
            math.isnan(v) for v in (open_val, high_val, low_val, close_val, volume_val)
        ):
            rows_dropped_missing += 1
            continue
        if ts_ms in seen_ts:
            duplicates_dropped += 1
            continue
        if ts_ms > now_ms:
            future_rows_dropped += 1
            continue
        seen_ts.add(ts_ms)
        zero_flag = 1 if volume_val == 0 else 0
        zero_volume_rows += zero_flag
        prepared.append(
            {
                "ts": ts_ms,
                "open": open_val,
                "high": high_val,
                "low": low_val,
                "close": close_val,
                "volume": volume_val,
                "zero_volume": zero_flag,
            }
        )

    prepared.sort(key=lambda item: item["ts"])
    canonical = pd.DataFrame.from_records(
        prepared,
        columns=["ts", "open", "high", "low", "close", "volume", "zero_volume"],
    )

    expected_closures, unexpected_gaps = _classify_calendar_gaps(canonical)

    # Apply adjustments if requested
    factors_digest: str | None = factors_digest_key
    if adjustment_policy == "full_adjusted":
        canonical = apply_full_adjustments(canonical, adjustment_factors)  # type: ignore[arg-type]

    hash_records: list[dict[str, float | int]]
    if adjustment_policy == "none":
        hash_records = prepared
    else:
        hash_records = [
            {
                "ts": int(row.ts),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
                "zero_volume": int(row.zero_volume),
            }
            for row in canonical.itertuples(index=False)
        ]

    # Compute raw digest on (possibly adjusted) canonical and incorporate policy
    raw_digest = _stable_dataframe_hash(hash_records)
    data_hash = (
        incorporate_policy_into_hash(raw_digest, adjustment_policy, factors_digest)
        if adjustment_policy != "none"
        else raw_digest
    )

    anomaly_counters: dict[str, int] = {
        "duplicates_dropped": duplicates_dropped,
        "rows_dropped_missing": rows_dropped_missing,
        "zero_volume_rows": zero_volume_rows,
        "future_rows_dropped": future_rows_dropped,
        "unexpected_gaps": unexpected_gaps,
        "expected_closures": expected_closures,
    }

    # Observed bar seconds (median delta); since NVDA dataset is daily we map declared 1d = 86400
    observed_bar_seconds: int | None = None
    if len(canonical) >= 2:
        deltas = canonical["ts"].diff().dropna().astype("int64") // 1000
        if not deltas.empty:
            observed_bar_seconds = int(deltas.median())
    declared_bar_seconds = 86400  # daily timeframe
    timeframe_ok = (
        (observed_bar_seconds == declared_bar_seconds) if observed_bar_seconds else None
    )
    if timeframe_ok is False:
        anomaly_counters["timeframe_mismatch"] = (
            anomaly_counters.get("timeframe_mismatch", 0) + 1
        )

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
        observed_bar_seconds=observed_bar_seconds,
        declared_bar_seconds=declared_bar_seconds,
        timeframe_ok=timeframe_ok,
        adjustment_policy=adjustment_policy,
        adjustment_factors_digest=factors_digest,
    )

    _DATASET_CACHE[cache_key] = (canonical, meta)
    _persist_metadata(meta)
    return canonical, meta


def get_dataset_metadata() -> DatasetMetadata:
    # Ensure default (none policy) is loaded
    canonical, meta = load_canonical_dataset()
    return meta


def _normalize_bound(value: int | float | None) -> float | None:
    if value is None:
        return None

    # Handle pandas/NumPy NA sentinels gracefully
    try:
        if pd.isna(value):
            return None
    except TypeError:
        # Some sentinels (e.g. numpy _NoValueType) raise when checked; treat as missing
        return None

    try:
        return float(value)
    except TypeError:
        return None


def slice_canonical(start_ms: int | None, end_ms: int | None) -> pd.DataFrame:
    """Return an immutable slice view of the canonical dataset.

    Parameters
    ----------
    start_ms, end_ms : int | None
        Inclusive (start) / inclusive (end) epoch ms boundaries. None leaves boundary open.
    """
    canonical, _ = load_canonical_dataset()
    view = canonical

    ts_values = pd.to_numeric(view["ts"], errors="coerce").to_numpy(
        dtype="float64", copy=False
    )
    valid_mask = ~np.isnan(ts_values)

    if not valid_mask.any():
        return view.iloc[[]].copy().reset_index(drop=True)

    valid_positions = np.nonzero(valid_mask)[0]
    valid_ts = ts_values[valid_positions]

    start_value = _normalize_bound(start_ms)
    end_value = _normalize_bound(end_ms)

    start_pos = 0
    if start_value is not None:
        start_pos = int(np.searchsorted(valid_ts, start_value, side="left"))

    end_pos = valid_ts.size
    if end_value is not None:
        end_pos = int(np.searchsorted(valid_ts, end_value, side="right"))

    if end_pos <= start_pos:
        return view.iloc[[]].copy().reset_index(drop=True)

    selected_positions = valid_positions[start_pos:end_pos]
    if selected_positions.size == 0:
        return view.iloc[[]].copy().reset_index(drop=True)

    data = {
        column: view[column].to_numpy(copy=True)[selected_positions]
        for column in view.columns
    }
    return pd.DataFrame(data, columns=view.columns).reset_index(drop=True)


def load_dataset_for(
    symbol: str, timeframe: str, data_dir: Path | None = None
) -> tuple[pd.DataFrame, DatasetMetadata]:
    """Generic facade (Phase J G04 prep). Currently only supports NVDA/1d; routes to existing loader.

    Once generic CSV logic is implemented this will dispatch by (symbol,timeframe,provider).
    """
    if symbol.upper() != SYMBOL or timeframe != TIMEFRAME:
        raise NotImplementedError(
            "Generic dataset loading not yet implemented for symbol/timeframe combination."
        )
    return load_canonical_dataset(data_dir)


def slice_dataset(
    symbol: str, timeframe: str, start_ms: int | None, end_ms: int | None
) -> pd.DataFrame:
    if symbol.upper() != SYMBOL or timeframe != TIMEFRAME:
        raise NotImplementedError(
            "Generic dataset slicing not yet implemented for symbol/timeframe combination."
        )
    return slice_canonical(start_ms, end_ms)


__all__ = [
    "DatasetMetadata",
    "get_dataset_metadata",
    "load_canonical_dataset",
    "load_dataset_for",
    "slice_canonical",
    "slice_dataset",
]
