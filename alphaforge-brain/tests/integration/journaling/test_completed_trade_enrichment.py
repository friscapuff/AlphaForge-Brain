from __future__ import annotations

import json
from datetime import datetime

import pytest
from models.completed_trade import CompletedTrade
from models.fill import Fill
from models.trade_context_snapshot import TradeContextSnapshot
from services.journaling import JOURNALING_ROOT, resolve_journaling_root
from services.journaling.enrichment import prepare_enriched_payload
from services.journaling.writer import write_journaling_artifacts


@pytest.fixture()
def journaling_root(tmp_path):
    base = resolve_journaling_root(tmp_path)
    assert base.is_dir()
    return base


def test_completed_trade_enrichment_exports_expected_fields(journaling_root):
    run_id = "run-journaling-001"

    trade = CompletedTrade(
        id="trade-001",
        schema_version="2025.10.16",
        symbol="AAPL",
        entry_ts=datetime.fromisoformat("2025-10-14T14:30:10+00:00"),
        exit_ts=datetime.fromisoformat("2025-10-14T15:45:05+00:00"),
        entry_price=185.12,
        exit_price=186.02,
        quantity=200,
        pnl=180.0,
        return_pct=0.004863,
        holding_period_secs=4500.0,
        signal_id="mean_revert_v3",
        signal_strength=0.72,
        decision_ts=datetime.fromisoformat("2025-10-14T14:29:55+00:00"),
        mae=0.0,
        mfe=0.0,
        r_multiple=0.0,
        expectancy_bucket="neutral",
        checklist_status="passed",
        risk_flag=None,
        context_snapshot_id="ctx-001",
        fills=[
            Fill(
                ts=datetime.fromisoformat("2025-10-14T14:30:10+00:00"),
                order_id="ord-001",
                size=200,
                price=185.12,
                run_id="run-journaling-001",
                stop_id="stop-mean",
                target_id="target-mean",
                risk_tier="moderate",
                expectancy_inputs={"risk_unit": 120.0, "spread_bps": 3.1},
            ),
            Fill(
                ts=datetime.fromisoformat("2025-10-14T14:55:05+00:00"),
                order_id="ord-002",
                size=-200,
                price=186.02,
                run_id="run-journaling-001",
                risk_tier="moderate",
            ),
        ],
    )

    snapshot = TradeContextSnapshot(
        id="ctx-001",
        schema_version="2025.10.16",
        trade_id="trade-001",
        collected_at=datetime.fromisoformat("2025-10-14T14:35:00+00:00"),
        market_symbol="AAPL",
        bid=185.1,
        ask=185.2,
        spread_bps=5.4,
        volatility_score=0.62,
        volume_window=125000.0,
        checklist={"pre_trade": "passed", "post_trade": "passed"},
        indicators={"atr": 0.8, "rsi": 62.0},
    )

    price_events = {"trade-001": [184.76, 186.94]}

    artifacts = prepare_enriched_payload(
        run_id,
        [trade],
        snapshots=[snapshot],
        price_events=price_events,
    )
    assert artifacts.aggregate is None
    assert artifacts.source_artifacts[0] == "completed_trades.json"
    result = write_journaling_artifacts(
        run_id,
        artifacts,
        base_dir=journaling_root,
    )
    assert result.aggregate_path is None

    completed_trades_path = result.trade_path
    with completed_trades_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert len(payload) == 1
    enriched = payload[0]
    assert enriched["mae"] == pytest.approx(0.36)
    assert enriched["mfe"] == pytest.approx(1.82)
    assert enriched["r_multiple"] == pytest.approx(1.5)
    assert enriched["expectancy_bucket"] == "positive"
    assert enriched["signal_id"] == "mean_revert_v3"
    assert enriched["context_snapshot_id"] == "ctx-001"
    assert enriched["hash_signature"] == result.signature

    assert JOURNALING_ROOT.name == "journaling"

    snapshot_dir = completed_trades_path.parent / "snapshots"
    assert (snapshot_dir / "trade-trade-001.json").is_file()
