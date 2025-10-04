from __future__ import annotations

from pathlib import Path

from infra import config as _config
from infra.db import get_connection
from infra.persistence import finalize_run, get_metrics, init_run


def test_finalize_run_inserts_rows_and_metrics(tmp_path: Path, monkeypatch) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "finalize.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "f" * 64
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
            "data_hash": "d" * 64,
            "seed_root": 42,
            "provenance": {"manifest_content_hash": "e" * 64},
            "causality_guard": {"mode": "STRICT", "violations": 0},
            "bootstrap": {
                "seed": 1,
                "trials": 0,
                "ci_level": 0.95,
                "method": "simple",
                "fallback": True,
            },
        },
        data_hash="d" * 64,
        seed_root=42,
        db_version=1,
        bootstrap_seed=123,
        walk_forward_spec=None,
    )

    trades = [
        (1000, "buy", 1.0, 10.0, None, 1.0, None, None, 1.0),
        (2000, "sell", 2.0, 12.0, 11.0, 1.0, None, None, -1.0),
    ]
    equity = [
        (1000, 100.0, 0.0, 0.0, 0.0, 0.0),
        (2000, 101.0, 0.0, 1.0, 0.0, 0.0),
        (3000, 99.0, 2.0, 0.0, -2.0, 0.0),
    ]

    n_trades, n_equity = finalize_run(
        run_hash=run_hash,
        trades_rows=trades,
        equity_rows=equity,
        record_counts_phase="finalize",
    )
    assert n_trades == 2
    assert n_equity == 3

    # Verify table counts and metrics rows
    with get_connection() as conn:
        t_count = conn.execute(
            "SELECT COUNT(*) AS c FROM trades WHERE run_hash=?", (run_hash,)
        ).fetchone()[0]
        e_count = conn.execute(
            "SELECT COUNT(*) AS c FROM equity WHERE run_hash=?", (run_hash,)
        ).fetchone()[0]
        assert t_count == 2
        assert e_count == 3
        mets = get_metrics(conn, run_hash)
        keys = {(m["key"], m.get("phase")) for m in mets}
        assert ("rows_trades", "finalize") in keys
        assert ("rows_equity", "finalize") in keys
