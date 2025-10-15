from __future__ import annotations

import pytest
from services.hashing import hash_enriched_journaling_payload


def _example_payload_variant(reverse: bool = False) -> dict[str, object]:
    trade_a = {
        "id": "trade-a",
        "symbol": "AAPL",
        "entry_ts": "2025-10-14T14:30:10Z",
        "exit_ts": "2025-10-14T15:45:05Z",
        "entry_price": 185.12,
        "exit_price": 186.02,
        "quantity": 200,
        "pnl": 180.0,
        "return_pct": 0.004863,
        "holding_period_secs": 4500.0,
        "mae": 0.42,
        "mfe": 1.24,
        "fills": [
            {
                "ts": "2025-10-14T14:30:10Z",
                "order_id": "ord-001",
                "price": 185.12,
                "size": 200,
                "stop_id": "stop-mean",
            },
            {
                "ts": "2025-10-14T15:45:05Z",
                "order_id": "ord-002",
                "price": 186.02,
                "size": -200,
                "target_id": "target-mean",
            },
        ],
    }

    trade_b = {
        "id": "trade-b",
        "symbol": "MSFT",
        "entry_ts": "2025-10-14T16:00:00Z",
        "exit_ts": "2025-10-14T16:45:00Z",
        "entry_price": 330.5,
        "exit_price": 331.2,
        "quantity": 150,
        "pnl": 105.0,
        "return_pct": 0.002118,
        "holding_period_secs": 2700.0,
        "mae": 0.18,
        "mfe": 0.95,
        "fills": [
            {
                "ts": "2025-10-14T16:30:00Z",
                "order_id": "ord-102",
                "price": 330.9,
                "size": -150,
            },
            {
                "ts": "2025-10-14T16:00:00Z",
                "order_id": "ord-101",
                "price": 330.5,
                "size": 150,
            },
        ],
    }

    snapshots = [
        {
            "id": "ctx-b",
            "trade_id": "trade-b",
            "collected_at": "2025-10-14T16:05:00Z",
            "schema_version": "2025.10.16",
            "market_symbol": "MSFT",
            "bid": 330.45,
            "ask": 330.55,
            "checklist": {"post_trade": "waived", "pre_trade": "passed"},
            "indicators": {"atr": 1.2, "rsi": 55.2},
        },
        {
            "id": "ctx-a",
            "trade_id": "trade-a",
            "collected_at": "2025-10-14T14:35:00Z",
            "schema_version": "2025.10.16",
            "market_symbol": "AAPL",
            "bid": 185.1,
            "ask": 185.2,
            "checklist": {"post_trade": "passed", "pre_trade": "passed"},
            "indicators": {"atr": 0.8, "rsi": 62.0},
        },
    ]

    aggregate = {
        "run_id": "run-123",
        "schema_version": "2025.10.16",
        "generated_at": "2025-10-14T17:00:00Z",
        "artifact_hash": "placeholder",
        "context_version": "v1",
        "expectancy_by_strategy": {"mean_revert_v3": 0.61, "momentum_v2": 0.43},
        "checklist_adherence": {"pre_trade": 1.0, "post_trade": 0.75},
        "risk_distribution": {"conservative": 1, "moderate": 1},
        "mae_mfe_stats": {"mae_avg": 0.30, "mfe_avg": 1.10},
        "breach_flags": ["policy:max_runs"],
        "source_artifacts": [
            "snapshots/trade-a.json",
            "trades/completed.json",
            "snapshots/trade-b.json",
        ],
    }

    trades = [trade_b, trade_a] if reverse else [trade_a, trade_b]
    snapshot_list = list(reversed(snapshots)) if reverse else snapshots
    source_artifacts = (
        list(reversed(aggregate["source_artifacts"]))
        if reverse
        else aggregate["source_artifacts"]
    )

    payload = {
        "completed_trades": trades,
        "snapshots": snapshot_list,
        "aggregate": {**aggregate, "source_artifacts": source_artifacts},
    }
    return payload


def test_journaling_hash_canonicalises_nested_structures():
    payload_a = _example_payload_variant(reverse=False)
    payload_b = _example_payload_variant(reverse=True)

    signature_a = hash_enriched_journaling_payload(payload_a)
    signature_b = hash_enriched_journaling_payload(payload_b)

    assert signature_a is not None
    assert signature_a == signature_b


def test_journaling_hash_none_payload():
    assert hash_enriched_journaling_payload(None) is None


def test_journaling_hash_rejects_raw_strings():
    with pytest.raises(TypeError):
        hash_enriched_journaling_payload("oops")
