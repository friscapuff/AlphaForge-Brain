"""Generic CSV ingestion (Phase J continuation of G04/G05).

Currently supports daily timeframe datasets with required columns and basic normalization.
Multi-symbol capable; integrates with dataset registry entries specifying path & calendar.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import SupportsFloat

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

from .adjustments import (
    AdjustmentFactors,
    AdjustmentPolicy,
    apply_full_adjustments,
    compute_factors_digest,
    incorporate_policy_into_hash,
)

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
    anomaly_counters: dict[str, int]
    created_at: int
    # Phase K enrichment (optional defaults follow non-defaults)
    observed_bar_seconds: int | None = None
    declared_bar_seconds: int | None = None
    timeframe_ok: bool | None = None
    # FR-104 additions
    adjustment_policy: str | None = None
    adjustment_factors_digest: str | None = None

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


_DATASET_CACHE: dict[tuple[str, str], tuple[pd.DataFrame, GenericDatasetMetadata]] = {}
_CACHE_DIR = Path(".cache/datasets")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if not missing:
        return df
    # Attempt legacy vendor format auto-mapping (e.g. NVDA_5y.csv) if required columns absent.
    # Expected legacy headers: Date, Close/Last, Volume, Open, High, Low
    legacy_required = {"Date", "Close/Last", "Volume", "Open", "High", "Low"}
    if legacy_required.issubset(set(df.columns)):
        mapped = pd.DataFrame()
        # Parse date (MM/DD/YYYY) into naive datetime; downstream _parse_timestamps will localize.
        mapped["timestamp"] = pd.to_datetime(
            df["Date"], format="%m/%d/%Y", errors="coerce"
        )
        # Normalize numeric price columns; strip $ and commas where present.
        for col in ["Open", "High", "Low"]:
            mapped[col.lower()] = pd.to_numeric(
                df[col]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False),
                errors="coerce",
            )
        mapped["close"] = pd.to_numeric(
            df["Close/Last"]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False),
            errors="coerce",
        )
        mapped["volume"] = pd.to_numeric(
            df["Volume"].astype(str).str.replace(",", "", regex=False), errors="coerce"
        ).astype("Int64")
        mapped = mapped[mapped["timestamp"].notna()].copy()
        # Coerce volume to plain int where possible (after dropping NaNs)
        if "volume" in mapped.columns:
            try:
                mapped["volume"] = mapped["volume"].astype("int64")
            except Exception:
                pass
        return mapped
    raise ValueError(f"Missing required columns: {missing}")


def _classify_calendar_gaps(
    canonical: pd.DataFrame, calendar_id: str | None
) -> tuple[int, int]:
    if canonical.empty or not calendar_id:
        return 0, 0
    cal = xcals.get_calendar(calendar_id)
    utc_series = pd.to_datetime(canonical["ts"], unit="ms", utc=True).dt.tz_convert(
        None
    )
    first = utc_series.iloc[0].normalize()
    last = utc_series.iloc[-1].normalize()
    schedule = cal.sessions_in_range(first, last)
    dataset_days = set(ts.normalize() for ts in utc_series)
    missing_sessions = [s for s in schedule if s.normalize() not in dataset_days]
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


def _compute_observed_bar_seconds(canonical: pd.DataFrame) -> int | None:
    if len(canonical) < 2:
        return None
    deltas = canonical["ts"].diff().dropna().astype("int64") // 1000
    if deltas.empty:
        return None
    # median seconds between bars
    return int(deltas.median())


def load_generic_csv(
    symbol: str,
    timeframe: str,
    path: Path,
    calendar_id: str | None,
    *,
    adjustment_policy: AdjustmentPolicy = "none",
    adjustment_factors: AdjustmentFactors | None = None,
) -> tuple[pd.DataFrame, GenericDatasetMetadata]:
    key = (symbol.upper(), timeframe)
    if key in _DATASET_CACHE:
        return _DATASET_CACHE[key]
    raw = _read_csv(path)
    row_count_raw = len(raw)
    records = raw.to_dict("records")
    prepared: list[dict[str, float | int]] = []
    duplicates_dropped = 0
    rows_dropped_missing = 0
    zero_volume_rows = 0
    future_rows_dropped = 0
    seen_ts: set[int] = set()
    now_ms = int(time.time() * 1000)
    assume_tz_name = "America/New_York"
    if calendar_id and calendar_id.upper() not in {"XNYS", "XNAS", "NASDAQ"}:
        assume_tz_name = "UTC"
    assume_zone = ZoneInfo(assume_tz_name)

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
        if timestamp_raw is None or pd.isna(timestamp_raw):
            rows_dropped_missing += 1
            continue
        ts_local: datetime
        if isinstance(timestamp_raw, pd.Timestamp):
            if timestamp_raw is pd.NaT:
                rows_dropped_missing += 1
                continue
            ts_local = timestamp_raw.to_pydatetime()
        elif isinstance(timestamp_raw, datetime):
            ts_local = timestamp_raw
        else:
            try:
                parsed = pd.to_datetime(timestamp_raw, errors="coerce")
            except Exception:
                parsed = pd.NaT
            if pd.isna(parsed):
                rows_dropped_missing += 1
                continue
            ts_local = parsed.to_pydatetime()
        if ts_local.tzinfo is None:
            ts_local = ts_local.replace(tzinfo=assume_zone)
        ts_ms = int(ts_local.astimezone(ZoneInfo("UTC")).timestamp() * 1000)
        if ts_ms in seen_ts:
            duplicates_dropped += 1
            continue
        if ts_ms > now_ms:
            future_rows_dropped += 1
            continue

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
    if not canonical.empty:
        canonical["ts"] = canonical["ts"].astype("int64")
        canonical["zero_volume"] = canonical["zero_volume"].astype("int8")

    expected_closures, unexpected_gaps = _classify_calendar_gaps(canonical, calendar_id)
    factors_digest: str | None = None
    if adjustment_policy == "full_adjusted":
        factors_digest = compute_factors_digest(adjustment_policy, adjustment_factors)
        canonical = apply_full_adjustments(canonical, adjustment_factors)  # type: ignore[arg-type]
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
    raw_digest = _stable_dataframe_hash(hash_records)
    data_hash = (
        incorporate_policy_into_hash(raw_digest, adjustment_policy, factors_digest)
        if adjustment_policy != "none"
        else raw_digest
    )
    counters: dict[str, int] = {
        "duplicates_dropped": duplicates_dropped,
        "rows_dropped_missing": rows_dropped_missing,
        "zero_volume_rows": zero_volume_rows,
        "future_rows_dropped": future_rows_dropped,
        "unexpected_gaps": unexpected_gaps,
        "expected_closures": expected_closures,
    }
    observed = _compute_observed_bar_seconds(canonical)
    # declared seconds (rough heuristic: map daily -> 86400, else parse numeric + unit) for now only daily supported
    declared = 86400 if timeframe == "1d" else None
    timeframe_ok = (observed == declared) if (observed and declared) else None
    if timeframe_ok is False:
        counters["timeframe_mismatch"] = counters.get("timeframe_mismatch", 0) + 1
    meta = GenericDatasetMetadata(
        symbol=symbol.upper(),
        timeframe=timeframe,
        data_hash=data_hash,
        calendar_id=calendar_id,
        row_count_raw=row_count_raw,
        row_count_canonical=len(canonical),
        first_ts=int(canonical["ts"].iloc[0]) if not canonical.empty else 0,
        last_ts=int(canonical["ts"].iloc[-1]) if not canonical.empty else 0,
        anomaly_counters=counters,
        created_at=int(time.time() * 1000),
        observed_bar_seconds=observed,
        declared_bar_seconds=declared,
        timeframe_ok=timeframe_ok,
        adjustment_policy=adjustment_policy,
        adjustment_factors_digest=factors_digest,
    )
    _DATASET_CACHE[key] = (canonical, meta)
    return canonical, meta


def slice_generic(
    symbol: str, timeframe: str, start_ms: int | None, end_ms: int | None
) -> pd.DataFrame:
    key = (symbol.upper(), timeframe)
    if key not in _DATASET_CACHE:
        raise KeyError("Dataset not loaded; call load_generic_csv first")
    canonical = _DATASET_CACHE[key][0]
    if canonical.empty:
        return canonical.copy()
    ts = canonical["ts"].to_numpy(dtype="int64", copy=False)
    mask = np.ones(len(ts), dtype=bool)
    if start_ms is not None:
        mask &= ts >= start_ms
    if end_ms is not None:
        mask &= ts <= end_ms
    if not mask.any():
        return canonical.iloc[0:0].copy()
    indices = np.flatnonzero(mask)
    data = {
        column: canonical[column].to_numpy(copy=True)[indices]
        for column in canonical.columns
    }
    return pd.DataFrame(data, columns=canonical.columns, copy=False)


__all__ = ["GenericDatasetMetadata", "load_generic_csv", "slice_generic"]
