from __future__ import annotations

import json
from datetime import datetime

import pytest
from models.completed_trade import CompletedTrade
from models.fill import Fill
from services.journaling.enrichment import prepare_enriched_payload
from services.journaling.writer import write_journaling_artifacts


@pytest.fixture()
def sample_trade():
    return CompletedTrade(
        id="trade-missing-snapshot",
        schema_version="2025.10.16",
        symbol="AAPL",
        entry_ts=datetime.fromisoformat("2025-10-14T10:00:00+00:00"),
        exit_ts=datetime.fromisoformat("2025-10-14T11:30:00+00:00"),
        entry_price=100.0,
        exit_price=101.5,
        quantity=50,
        pnl=75.0,
        return_pct=0.015,
        holding_period_secs=5400.0,
        signal_id="gap_open",
        signal_strength=0.55,
        decision_ts=datetime.fromisoformat("2025-10-14T09:59:30+00:00"),
        mae=0.0,
        mfe=0.0,
        r_multiple=0.0,
        expectancy_bucket="neutral",
        checklist_status="waived",
        risk_flag="elevated_position",
        context_snapshot_id="ctx-missing",
        fills=[
            Fill(
                ts=datetime.fromisoformat("2025-10-14T10:00:00+00:00"),
                order_id="ord-300",
                size=50,
                price=100.0,
                stop_id="stop-gap",
                target_id="target-gap",
                risk_tier="aggressive",
            )
        ],
    )


def test_missing_snapshot_reason_codes(tmp_path, sample_trade):
    artifacts = prepare_enriched_payload(
        run_id="run-snapshot-gap",
        trades=[sample_trade],
        snapshots=[],
        price_events={"trade-missing-snapshot": [99.5, 103.2]},
    )

    result = write_journaling_artifacts(
        "run-snapshot-gap",
        artifacts,
        base_dir=tmp_path,
    )

    assert result.reasons_path is not None
    with result.reasons_path.open("r", encoding="utf-8") as handle:
        reasons = json.load(handle)

    assert len(reasons) == 1
    reason = reasons[0]
    assert reason["trade_id"] == "trade-missing-snapshot"
    assert reason["code"] == "snapshot_missing"
    assert "ctx-missing" in reason["detail"]
