from __future__ import annotations

from pathlib import Path

from infra import config as _config
from infra.db import get_connection
from infra.persistence import init_run, record_causality_stats


def test_record_causality_stats_updates_metrics_and_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "cguard.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "c" * 64
    init_run(
        run_hash=run_hash,
        created_at_ms=1,
        status="pending",
        config_json={"cfg": 1},
        manifest_json={
            "schema_version": 1,
            "run_hash": run_hash,
            "db_version": 1,
            "created_at": 1,
            "updated_at": 1,
            "status": "pending",
            "data_hash": "2" * 64,
            "seed_root": 42,
            "provenance": {"manifest_content_hash": "3" * 64},
            "causality_guard": {"mode": "STRICT", "violations": 0},
            "bootstrap": {
                "seed": 1,
                "trials": 0,
                "ci_level": 0.95,
                "method": "simple",
                "fallback": True,
            },
        },
        data_hash="2" * 64,
        seed_root=42,
        db_version=1,
        bootstrap_seed=123,
        walk_forward_spec=None,
    )

    record_causality_stats(
        run_hash=run_hash, mode="PERMISSIVE", violations=7, phase="execution"
    )

    with get_connection() as conn:
        mets = conn.execute(
            "SELECT key, value FROM metrics WHERE run_hash=?", (run_hash,)
        ).fetchall()
        d = {m[0]: m[1] for m in mets}
        assert d.get("causality_mode") == "PERMISSIVE"
        assert d.get("future_access_violations") == "7"
        import json

        manifest = json.loads(
            conn.execute(
                "SELECT manifest_json FROM runs WHERE run_hash=?", (run_hash,)
            ).fetchone()[0]
        )
        assert manifest.get("causality_guard", {}).get("mode") == "PERMISSIVE"
        assert manifest.get("causality_guard", {}).get("violations") == 7
