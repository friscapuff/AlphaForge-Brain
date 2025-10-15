from __future__ import annotations

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest
from models.completed_trade import CompletedTrade
from models.fill import Fill
from models.trade_context_snapshot import TradeContextSnapshot
from services.journaling.enrichment import prepare_enriched_payload
from services.journaling.writer import write_journaling_artifacts

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "journaling"
    / "export_to_cold_storage.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "journaling_export_to_cold_storage", _SCRIPT_PATH
)
assert _SPEC and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
export_to_cold_storage = _MODULE.export_to_cold_storage


def _sample_trades(
    run_id: str,
) -> tuple[list[CompletedTrade], list[TradeContextSnapshot]]:
    trades = [
        CompletedTrade(
            id="trade-cold-001",
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
            mae=0.12,
            mfe=0.32,
            r_multiple=0.8,
            expectancy_bucket="positive",
            checklist_status="passed",
            risk_flag=None,
            context_snapshot_id="ctx-cold-001",
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
    ]

    snapshots = [
        TradeContextSnapshot(
            id="ctx-cold-001",
            trade_id="trade-cold-001",
            collected_at=datetime.fromisoformat("2025-10-14T14:30:05+00:00"),
            market_symbol="AAPL",
            bid=185.10,
            ask=185.12,
            spread_bps=1.1,
            volatility_score=22.0,
            checklist={"reviewed": "true", "risk": "green"},
        )
    ]

    return trades, snapshots


@pytest.mark.integration
def test_export_writes_archive_and_retention_log(tmp_path: Path) -> None:
    run_id = "run-cold-export-001"
    journaling_root = tmp_path / "journaling"
    artifact_root = tmp_path / "artifacts"
    retention_log = tmp_path / "retention_audit.log"

    trades, snapshots = _sample_trades(run_id)
    payload = prepare_enriched_payload(run_id, trades, snapshots=snapshots)
    write_journaling_artifacts(run_id, payload, base_dir=journaling_root)

    metadata = export_to_cold_storage(
        run_id,
        journaling_root=journaling_root,
        artifact_root=artifact_root,
        retention_log=retention_log,
        upload=False,
    )

    archive_path = Path(metadata["archive_path"])
    assert archive_path.exists(), "archive should remain locally after export"

    metadata_path = Path(metadata["metadata_path"])
    assert metadata_path.exists(), "metadata manifest must be written"

    written_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert written_metadata["run_id"] == run_id
    assert written_metadata.get("hash_signature")
    assert "completed_trades.json" in written_metadata.get("files", [])
    assert written_metadata.get("source_artifacts")

    exported_at = datetime.fromisoformat(written_metadata["exported_at"])
    assert exported_at.tzinfo is not None

    log_lines = retention_log.read_text(encoding="utf-8").strip().splitlines()
    assert log_lines, "retention audit log should receive an entry"
    log_entry = json.loads(log_lines[-1])

    assert log_entry["event"] == "journaling.cold_storage.exported"
    assert log_entry["run_id"] == run_id
    assert log_entry["archive_path"] == written_metadata["archive_path"]
    assert log_entry["file_count"] == written_metadata["file_count"]

    deadline_at = datetime.fromisoformat(log_entry["deadline_at"])
    assert deadline_at.tzinfo is not None
    delta_hours = (deadline_at - exported_at).total_seconds() / 3600
    assert pytest.approx(delta_hours, rel=1e-4) == 24.0

    # Ensure the log entry cites the same source artifacts tracked by the aggregate
    assert sorted(log_entry["source_artifacts"]) == sorted(
        written_metadata.get("source_artifacts", [])
    )
