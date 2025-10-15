from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from models.completed_trade import CompletedTrade
from models.fill import Fill
from models.trade_context_snapshot import TradeContextSnapshot
from services.journaling.enrichment import prepare_enriched_payload
from services.journaling.writer import write_journaling_artifacts

pytestmark = pytest.mark.skip(reason="Journaling aggregate arrives in Phase 5")


def _build_trades(
    run_id: str,
) -> tuple[list[CompletedTrade], list[TradeContextSnapshot]]:
    trades = [
        CompletedTrade(
            id="trade-replay-001",
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
            context_snapshot_id="ctx-replay-001",
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
            id="trade-replay-002",
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
            context_snapshot_id="ctx-replay-002",
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
            id="ctx-replay-001",
            trade_id="trade-replay-001",
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
            id="ctx-replay-002",
            trade_id="trade-replay-002",
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
    return trades, snapshots


def _assert_within_variance(
    base: float, other: float, tolerance: float = 0.001
) -> None:
    if base == pytest.approx(0.0):
        assert other == pytest.approx(0.0, abs=1e-6)
        return
    delta = abs(base - other)
    allowed = abs(base) * tolerance
    assert delta <= allowed + 1e-9


def test_journaling_aggregate_replay_variance(tmp_path: Path) -> None:
    run_id = "run-journaling-replay"
    trades, snapshots = _build_trades(run_id)
    price_events = {
        "trade-replay-001": [184.76, 186.94],
        "trade-replay-002": [331.55, 329.90],
    }

    artifacts_a = prepare_enriched_payload(
        run_id,
        trades,
        snapshots=snapshots,
        price_events=price_events,
    )
    # Replay with reversed ordering to confirm determinism
    artifacts_b = prepare_enriched_payload(
        run_id,
        list(reversed(trades)),
        snapshots=list(reversed(snapshots)),
        price_events=price_events,
    )

    assert artifacts_a.aggregate is not None
    assert artifacts_b.aggregate is not None

    aggregate_a = artifacts_a.aggregate
    aggregate_b = artifacts_b.aggregate

    assert aggregate_a.artifact_hash == aggregate_b.artifact_hash
    assert aggregate_a.source_artifacts == aggregate_b.source_artifacts

    for signal_id, value in aggregate_a.expectancy_by_strategy.items():
        assert signal_id in aggregate_b.expectancy_by_strategy
        _assert_within_variance(value, aggregate_b.expectancy_by_strategy[signal_id])

    for rule, value in aggregate_a.checklist_adherence.items():
        assert rule in aggregate_b.checklist_adherence
        _assert_within_variance(value, aggregate_b.checklist_adherence[rule])

    for metric, value in aggregate_a.mae_mfe_stats.items():
        assert metric in aggregate_b.mae_mfe_stats
        _assert_within_variance(value, aggregate_b.mae_mfe_stats[metric])

    assert aggregate_a.risk_distribution == aggregate_b.risk_distribution
    assert aggregate_a.breach_flags == aggregate_b.breach_flags

    # Confirm writing aggregates preserves determinism across file outputs
    first_result = write_journaling_artifacts(
        run_id,
        artifacts_a,
        base_dir=tmp_path / "first",
    )
    second_result = write_journaling_artifacts(
        run_id,
        artifacts_b,
        base_dir=tmp_path / "second",
    )
    assert first_result.aggregate_path is not None
    assert second_result.aggregate_path is not None
    assert first_result.aggregate_path.read_text(
        encoding="utf-8"
    ) == second_result.aggregate_path.read_text(encoding="utf-8")
