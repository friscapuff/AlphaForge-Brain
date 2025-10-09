from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from infra import config as _config
from infra.db import get_connection
from infra.persistence import init_run


def _load_script_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("unify_trades", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_t097_runs_extras_backfill_persists_caution_and_metrics(
    sqlite_tmp_path: Path, monkeypatch
) -> None:
    """
    Validation Persistence Test (T097):
    - Migration adds runs_extras columns (validation_caution, validation_caution_metrics)
    - Apply updates backfills values from manifest JSON
    - Verify persisted rows reflect manifest values (1/0/null and JSON list)
    """

    class _TempSettings(_config.Settings):
        sqlite_path: Path = sqlite_tmp_path

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    # Seed two runs: one with caution True + metrics, one without fields
    run_true = "a" * 64
    man_true = {
        "schema_version": 1,
        "run_hash": run_true,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "0" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "0" * 64},
        "validation_caution": True,
        "validation_caution_metrics": ["permutation", "block_bootstrap"],
    }
    run_none = "b" * 64
    man_none = {
        "schema_version": 1,
        "run_hash": run_none,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "1" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "1" * 64},
    }

    for rh, m in ((run_true, man_true), (run_none, man_none)):
        init_run(
            run_hash=rh,
            created_at_ms=1,
            status="complete",
            config_json={},
            manifest_json=m,
            data_hash=m["data_hash"],
            seed_root=1,
            db_version=1,
            bootstrap_seed=1,
            walk_forward_spec=None,
        )

    # Load migration script and apply discovered updates
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "migrations"
        / "unify_trades.py"
    )
    mod = _load_script_module(script_path)
    updates = mod.discover_updates()
    applied = mod.apply_updates(updates)
    assert applied >= 2

    # Inspect persisted values
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT run_hash, validation_caution, validation_caution_metrics FROM runs_extras"
        ).fetchall()
        got = {r[0]: (r[1], r[2]) for r in rows}

    assert got[run_true][0] == 1
    assert json.loads(got[run_true][1]) == ["permutation", "block_bootstrap"]

    # Absent in manifest -> NULLs remain
    assert got[run_none][0] is None and got[run_none][1] is None
