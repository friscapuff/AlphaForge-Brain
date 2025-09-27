"""Generic CSV ingestion (Phase J continuation of G04/G05).

Currently supports daily timeframe datasets with required columns and basic normalization.
Multi-symbol capable; integrates with dataset registry entries specifying path & calendar.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
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
        mapped = mapped.dropna(
            subset=["timestamp"]
        )  # drop rows where date failed to parse
        # Coerce volume to plain int where possible (after dropping NaNs)
        if "volume" in mapped.columns:
            try:
                mapped["volume"] = mapped["volume"].astype("int64")
            except Exception:
                pass
        return mapped
    raise ValueError(f"Missing required columns: {missing}")


def _parse_timestamps(df: pd.DataFrame, tz: str = "America/New_York") -> pd.DataFrame:
    out = df.copy()
    out["ts"] = to_epoch_ms(out["timestamp"], assume_tz=tz)
    return out


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


def _stable_dataframe_hash(df: pd.DataFrame) -> str:
    core = df[["ts", "open", "high", "low", "close", "volume", "zero_volume"]].copy()
    core.sort_values("ts", inplace=True)
    csv_bytes = core.to_csv(
        index=False, lineterminator="\n", float_format="%.8f"
    ).encode()
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
    df = _parse_timestamps(raw)
    df = df.sort_values("ts", kind="mergesort").reset_index(drop=True)
    before_dupes = len(df)
    df = df[~df["ts"].duplicated(keep="first")].copy()
    duplicates_dropped = before_dupes - len(df)
    critical = ["open", "high", "low", "close", "volume"]
    before_missing = len(df)
    df = df.dropna(subset=critical)
    rows_dropped_missing = before_missing - len(df)
    df["zero_volume"] = (df["volume"] == 0).astype("int8")
    zero_volume_rows = int(df["zero_volume"].sum())
    now_ms = int(time.time() * 1000)
    before_future = len(df)
    df = df[df["ts"] <= now_ms]
    future_rows_dropped = before_future - len(df)
    expected_closures, unexpected_gaps = _classify_calendar_gaps(df, calendar_id)
    canonical_cols = ["ts", "open", "high", "low", "close", "volume", "zero_volume"]
    canonical = df[canonical_cols].copy()
    factors_digest: str | None = None
    if adjustment_policy == "full_adjusted":
        factors_digest = compute_factors_digest(adjustment_policy, adjustment_factors)
        canonical = apply_full_adjustments(canonical, adjustment_factors)  # type: ignore[arg-type]
    raw_digest = _stable_dataframe_hash(canonical)
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
    mask = pd.Series(True, index=canonical.index)
    if start_ms is not None:
        mask &= canonical["ts"] >= start_ms
    if end_ms is not None:
        mask &= canonical["ts"] <= end_ms
    return canonical.loc[mask].copy().reset_index(drop=True)


__all__ = ["GenericDatasetMetadata", "load_generic_csv", "slice_generic"]
