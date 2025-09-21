from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from domain.data.ingest_nvda import DatasetMetadata, get_dataset_metadata


@dataclass(slots=True)
class ValidationSummary:
    symbol: str
    timeframe: str
    calendar_id: str
    data_hash: str
    row_count_raw: int
    row_count_canonical: int
    first_ts: int
    last_ts: int
    anomaly_counters: Dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # enforce deterministic ordering by reconstructing (Python 3.7+ preserves insertion order)
        ordered = {
            "symbol": d["symbol"],
            "timeframe": d["timeframe"],
            "calendar_id": d["calendar_id"],
            "data_hash": d["data_hash"],
            "row_count_raw": d["row_count_raw"],
            "row_count_canonical": d["row_count_canonical"],
            "first_ts": d["first_ts"],
            "last_ts": d["last_ts"],
            "anomaly_counters": d["anomaly_counters"],
        }
        return ordered


def build_validation_summary(meta: DatasetMetadata | None = None) -> ValidationSummary:
    if meta is None:
        meta = get_dataset_metadata()
    return ValidationSummary(
        symbol=meta.symbol,
        timeframe=meta.timeframe,
        calendar_id=meta.calendar_id,
        data_hash=meta.data_hash,
        row_count_raw=meta.row_count_raw,
        row_count_canonical=meta.row_count_canonical,
        first_ts=meta.first_ts,
        last_ts=meta.last_ts,
        anomaly_counters=dict(meta.anomaly_counters),
    )
