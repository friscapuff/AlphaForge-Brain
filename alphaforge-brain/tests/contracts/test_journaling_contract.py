from __future__ import annotations

import json
import string
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import validate as jsonschema_validate
from models.completed_trade import CompletedTrade
from models.fill import Fill
from models.trade_context_snapshot import TradeContextSnapshot
from services.journaling.enrichment import prepare_enriched_payload
from services.journaling.writer import write_journaling_artifacts

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "alphaforge-brain"
    / "contracts"
    / "journaling_contract.schema.json"
)


def _wrap_definition(schema: dict[str, object], ref: str) -> dict[str, object]:
    wrapped: dict[str, object] = {
        "$schema": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
        "$ref": ref,
    }
    if "$defs" in schema:
        wrapped["$defs"] = schema["$defs"]
    if "definitions" in schema:
        wrapped["definitions"] = schema["definitions"]
    return wrapped


@pytest.mark.contract
def test_journaling_artifacts_match_contract(tmp_path: Path) -> None:
    schema = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))

    run_id = "run-journaling-contract"
    trades = [
        CompletedTrade(
            id="trade-001",
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
                    run_id=run_id,
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
                    run_id=run_id,
                    risk_tier="moderate",
                ),
            ],
        ),
        CompletedTrade(
            id="trade-002",
            symbol="MSFT",
            entry_ts=datetime.fromisoformat("2025-10-14T15:00:00+00:00"),
            exit_ts=datetime.fromisoformat("2025-10-14T16:10:00+00:00"),
            entry_price=330.87,
            exit_price=332.11,
            quantity=-150,
            pnl=-120.5,
            return_pct=-0.00375,
            holding_period_secs=4200.0,
            signal_id="momentum_short",
            signal_strength=-0.55,
            decision_ts=datetime.fromisoformat("2025-10-14T14:59:45+00:00"),
            mae=0.0,
            mfe=0.0,
            r_multiple=0.0,
            expectancy_bucket="neutral",
            checklist_status="waived",
            risk_flag=None,
            context_snapshot_id="ctx-002",
            fills=[
                Fill(
                    ts=datetime.fromisoformat("2025-10-14T15:00:01+00:00"),
                    order_id="ord-101",
                    size=-75,
                    price=330.80,
                    run_id=run_id,
                    risk_tier="aggressive",
                ),
                Fill(
                    ts=datetime.fromisoformat("2025-10-14T16:10:00+00:00"),
                    order_id="ord-102",
                    size=-75,
                    price=332.11,
                    run_id=run_id,
                    risk_tier="conservative",
                ),
            ],
        ),
    ]

    snapshots = [
        TradeContextSnapshot(
            id="ctx-001",
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
        ),
        TradeContextSnapshot(
            id="ctx-002",
            trade_id="trade-002",
            collected_at=datetime.fromisoformat("2025-10-14T15:05:00+00:00"),
            market_symbol="MSFT",
            bid=330.7,
            ask=330.9,
            spread_bps=6.2,
            volatility_score=0.48,
            volume_window=98000.0,
            checklist={"pre_trade": "waived", "post_trade": "passed"},
            indicators={"atr": 1.1, "rsi": 38.0},
        ),
    ]

    price_events = {
        "trade-001": [184.76, 186.94],
        "trade-002": [331.55, 329.90],
    }

    artifacts = prepare_enriched_payload(
        run_id,
        trades,
        snapshots=snapshots,
        price_events=price_events,
    )
    result = write_journaling_artifacts(
        run_id,
        artifacts,
        base_dir=tmp_path,
    )
    assert result.trade_path.is_file()
    assert result.signature
    assert result.aggregate_path is not None
    assert result.aggregate_path.is_file()

    aggregate_payload = json.loads(result.aggregate_path.read_text(encoding="utf-8"))
    datetime.fromisoformat(aggregate_payload["generated_at"])
    assert len(aggregate_payload["artifact_hash"]) == 64
    assert set(aggregate_payload["source_artifacts"]).issuperset(
        {"completed_trades.json"}
    )
    assert all(
        not Path(item).is_absolute() for item in aggregate_payload["source_artifacts"]
    )

    aggregate_schema = _wrap_definition(schema, "#/$defs/JournalingAggregate")
    jsonschema_validate(instance=aggregate_payload, schema=aggregate_schema)

    trade_payload = json.loads(result.trade_path.read_text(encoding="utf-8"))
    assert len(trade_payload) == len(trades)
    trade_schema = _wrap_definition(schema, "#/$defs/CompletedTradeRecord")
    for entry in trade_payload:
        jsonschema_validate(instance=entry, schema=trade_schema)
        assert entry["hash_signature"] == result.signature

    assert {
        "mean_revert_v3",
        "momentum_short",
    }.issubset(aggregate_payload["expectancy_by_strategy"].keys())
    assert aggregate_payload["checklist_adherence"]
    assert aggregate_payload["risk_distribution"]
    assert set(aggregate_payload["expectancy_by_strategy"].keys()) == {
        "mean_revert_v3",
        "momentum_short",
    }
    assert all(
        isinstance(value, float) and not isinstance(value, bool)
        for value in aggregate_payload["expectancy_by_strategy"].values()
    )
    assert all(ch in string.hexdigits for ch in aggregate_payload["artifact_hash"])
    assert isinstance(aggregate_payload["breach_flags"], list)
