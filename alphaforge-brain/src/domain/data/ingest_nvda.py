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
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

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


def _stable_dataframe_hash(df: pd.DataFrame) -> str:
    # Use only canonical columns for hash; ensure sorted by ts
    core = df[["ts", "open", "high", "low", "close", "volume", "zero_volume"]].copy()
    core.sort_values("ts", inplace=True)
    # Deterministic CSV bytes (float precision limited for stability)
    csv_bytes = core.to_csv(
        index=False, lineterminator="\n", float_format="%.8f"
    ).encode("utf-8")
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

    # Apply adjustments if requested
    factors_digest: str | None = factors_digest_key
    if adjustment_policy == "full_adjusted":
        canonical = apply_full_adjustments(canonical, adjustment_factors)  # type: ignore[arg-type]
    # Compute raw digest on (possibly adjusted) canonical and incorporate policy
    raw_digest = _stable_dataframe_hash(canonical)
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
