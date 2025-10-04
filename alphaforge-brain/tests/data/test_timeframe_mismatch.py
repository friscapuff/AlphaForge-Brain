from __future__ import annotations

from domain.data.ingest_nvda import DatasetMetadata
from domain.validation.summary.model import build_validation_summary


def test_validation_summary_timeframe_fields_present() -> None:
    # Use synthetic metadata objects to validate presence of new timeframe fields.
    meta = DatasetMetadata(
        symbol="NVDA",
        timeframe="1d",
        data_hash="abc",
        calendar_id="NASDAQ",
        row_count_raw=10,
        row_count_canonical=10,
        first_ts=1,
        last_ts=10,
        anomaly_counters={},
        created_at=0,
        observed_bar_seconds=86400,
        declared_bar_seconds=86400,
        timeframe_ok=True,
    )
    summary = build_validation_summary(meta)
    d = summary.to_dict()
    assert d["observed_bar_seconds"] == 86400
    assert d["declared_bar_seconds"] == 86400
    assert d["timeframe_ok"] is True


def test_timeframe_mismatch_flagging() -> None:
    # Construct a mismatch scenario: observed 3600 (pretend hourly) but declared daily.
    meta = DatasetMetadata(
        symbol="NVDA",
        timeframe="1d",
        data_hash="def",
        calendar_id="NASDAQ",
        row_count_raw=10,
        row_count_canonical=10,
        first_ts=1,
        last_ts=10,
        anomaly_counters={"timeframe_mismatch": 1},
        created_at=0,
        observed_bar_seconds=3600,
        declared_bar_seconds=86400,
        timeframe_ok=False,
    )
    summary = build_validation_summary(meta)
    d = summary.to_dict()
    assert d["timeframe_ok"] is False
    assert d["observed_bar_seconds"] == 3600
    assert d["declared_bar_seconds"] == 86400
    assert d["anomaly_counters"].get("timeframe_mismatch") == 1
