from __future__ import annotations

from pathlib import Path

from infra import config as _config
from infra.db import get_connection
from infra.persistence import init_run, insert_validation


def test_validation_metrics_persist(sqlite_tmp_path: Path, monkeypatch) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = sqlite_tmp_path

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "v" * 64
    init_run(
        run_hash=run_hash,
        created_at_ms=1,
        status="pending",
        config_json={},
        manifest_json={
            "schema_version": 1,
            "run_hash": run_hash,
            "db_version": 1,
            "created_at": 1,
            "updated_at": 1,
            "status": "pending",
            "data_hash": "0" * 64,
            "seed_root": 1,
            "provenance": {"manifest_content_hash": "0" * 64},
        },
        data_hash="0" * 64,
        seed_root=1,
        db_version=1,
        bootstrap_seed=1,
        walk_forward_spec=None,
    )
    payload = {
        "summary": {
            "permutation_p": 0.1,
            "block_bootstrap_p": 0.2,
            "block_bootstrap_ci_width": 0.05,
            "walk_forward_folds": 4,
        }
    }
    insert_validation(
        run_hash=run_hash,
        payload_json=payload,
        permutation_pvalue=0.1,
        method="hadj_bb",
        sharpe_ci=(0.0, 0.1),
        cagr_ci=None,
        block_length=10,
        jitter=0,
        fallback=False,
    )
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value, phase FROM metrics WHERE run_hash=? AND phase='validation'",
            (run_hash,),
        ).fetchall()
        keys = {r[0] for r in rows}
        assert {
            "validation_perm_p",
            "validation_bb_p",
            "validation_bb_ci_width",
            "validation_wf_folds",
        }.issubset(keys)
