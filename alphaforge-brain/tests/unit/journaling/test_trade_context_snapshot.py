from __future__ import annotations

from datetime import datetime

from models.trade_context_snapshot import TradeContextSnapshot
from services.hashing import hash_enriched_journaling_payload
from services.journaling.enrichment import prepare_enriched_payload


def test_snapshot_hashing_is_deterministic():
    snapshot_a = TradeContextSnapshot(
        id="ctx-A",
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

    snapshot_b = TradeContextSnapshot(
        id="ctx-B",
        schema_version="2025.10.16",
        trade_id="trade-002",
        collected_at=datetime.fromisoformat("2025-10-14T14:40:00+00:00"),
        market_symbol="MSFT",
        bid=330.45,
        ask=330.55,
        spread_bps=3.1,
        volatility_score=0.48,
        volume_window=91000.0,
        checklist={"pre_trade": "waived", "post_trade": "passed"},
        indicators={"atr": 1.2, "rsi": 55.2},
    )

    payload_one = {
        "snapshots": [
            snapshot_a.model_dump(mode="json"),
            snapshot_b.model_dump(mode="json"),
        ]
    }
    payload_two = {
        "snapshots": [
            snapshot_b.model_dump(mode="json"),
            snapshot_a.model_dump(mode="json"),
        ]
    }

    assert hash_enriched_journaling_payload(
        payload_one
    ) == hash_enriched_journaling_payload(payload_two)


def test_prepare_enriched_payload_handles_zero_trades():
    artifacts = prepare_enriched_payload(
        run_id="run-empty",
        trades=[],
        snapshots=[],
    )

    assert artifacts.trades == []
    assert artifacts.snapshots == []
    assert artifacts.reasons == []
    assert artifacts.signature is not None
