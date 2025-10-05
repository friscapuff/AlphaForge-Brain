from __future__ import annotations

import hashlib
import json
from pathlib import Path

from infra import config as _config
from infra.db import get_connection
from infra.persistence import (
    bulk_insert_equity,
    bulk_insert_trades,
    get_metrics,
    get_run,
    init_run,
    insert_metric,
    insert_validation,
    update_run_status,
)


def test_persistence_roundtrip(tmp_path: Path, monkeypatch) -> None:
    # Point settings at a temp DB
    # Override settings to use a temporary SQLite path for this test
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "test.db"

    # Clear lru_cache and patch the function to return our temp settings
    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "a" * 64
    init_run(
        run_hash=run_hash,
        created_at_ms=1_700_000_000_000,
        status="pending",
        config_json={"x": 1},
        manifest_json={
            "schema_version": 1,
            "run_hash": run_hash,
            "db_version": 1,
            "created_at": 1,
            "updated_at": 1,
            "status": "pending",
            "data_hash": "b" * 64,
            "seed_root": 42,
            "provenance": {"manifest_content_hash": "c" * 64},
            "causality_guard": {"mode": "STRICT", "violations": 0},
            "bootstrap": {
                "seed": 1,
                "trials": 0,
                "ci_level": 0.95,
                "method": "simple",
                "fallback": True,
            },
        },
        data_hash="b" * 64,
        seed_root=42,
        db_version=1,
        bootstrap_seed=123,
        walk_forward_spec=None,
    )
    update_run_status(
        run_hash=run_hash, status="running", updated_at_ms=1_700_000_000_100
    )
    # Insert a couple rows
    bulk_insert_trades(
        run_hash=run_hash,
        rows=[(0, "buy", 1.0, 10.0, None, 1.0, None, None, 1.0)],
    )
    bulk_insert_equity(
        run_hash=run_hash,
        rows=[(0, 100.0, 0.0, 0.0, 0.0, 0.0)],
    )
    insert_metric(
        run_hash=run_hash,
        key="rows_trades",
        value="1",
        value_type="int",
        phase="finalize",
    )
    insert_validation(
        run_hash=run_hash,
        payload_json={"ok": True},
        permutation_pvalue=None,
        method="simple",
        sharpe_ci=(None, None),
        cagr_ci=(None, None),
        block_length=None,
        jitter=None,
        fallback=True,
    )

    # Verify reads and content re-materialization via canonical hashing
    with get_connection() as conn:
        row = get_run(conn, run_hash)
        assert row is not None
        assert row["status"] in {"pending", "running", "completed"}
        mets = get_metrics(conn, run_hash)
        assert any(m["key"] == "rows_trades" for m in mets)
        # Rematerialize trades/equity and compare content hash with original input rows
        t_rows = conn.execute(
            "SELECT ts, side, qty, entry_price, exit_price, cost_bps, borrow_cost, pnl, position_after FROM trades WHERE run_hash=? ORDER BY ts",
            (run_hash,),
        ).fetchall()
        e_rows = conn.execute(
            "SELECT ts, equity, drawdown, realized_pnl, unrealized_pnl, cost_drag FROM equity WHERE run_hash=? ORDER BY ts",
            (run_hash,),
        ).fetchall()
        # Build canonical digests
        original_trades = [(0, "buy", 1.0, 10.0, None, 1.0, None, None, 1.0)]
        original_equity = [(0, 100.0, 0.0, 0.0, 0.0, 0.0)]

        def _canon(x: object) -> str:
            return json.dumps(
                x, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )

        def _sha(text: str) -> str:
            return hashlib.sha256(text.encode("utf-8")).hexdigest()

        digest_in_trades = _sha(_canon(original_trades))
        digest_db_trades = _sha(_canon([tuple(r) for r in t_rows]))
        digest_in_equity = _sha(_canon(original_equity))
        digest_db_equity = _sha(_canon([tuple(r) for r in e_rows]))
        assert digest_in_trades == digest_db_trades
        assert digest_in_equity == digest_db_equity
