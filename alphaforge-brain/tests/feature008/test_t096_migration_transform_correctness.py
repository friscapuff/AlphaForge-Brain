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


def test_t096_apply_persists_expected_fields_and_counts(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Executes the migration apply-mode on a small fixture DB with a mix of runs and
    verifies:
      - runs_extras rows are created for all runs
      - validation_caution (normalized to 0/1) and metrics list JSON persisted correctly
      - trade_model_version string is persisted when present
    """

    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "t096.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    # Seed three runs with different shapes
    run_a = "1" * 64  # vc True -> 1, has metrics & version
    man_a = {
        "schema_version": 1,
        "run_hash": run_a,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "a" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "a" * 64},
        "validation_caution": True,
        "validation_caution_metrics": ["permutation", "block_bootstrap"],
        "trade_model_version": "2",
    }
    run_b = "2" * 64  # vc False -> 0, metrics empty list
    man_b = {
        "schema_version": 1,
        "run_hash": run_b,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "b" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "b" * 64},
        "validation_caution": False,
        "validation_caution_metrics": [],
    }
    run_c = "3" * 64  # no fields -> NULLs
    man_c = {
        "schema_version": 1,
        "run_hash": run_c,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "c" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "c" * 64},
    }
    for rh, m in ((run_a, man_a), (run_b, man_b), (run_c, man_c)):
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

    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "migrations"
        / "unify_trades.py"
    )
    mod = _load_script_module(script_path)
    updates = mod.discover_updates()
    # All three runs must appear
    assert {u.run_hash for u in updates} >= {run_a, run_b, run_c}
    applied = mod.apply_updates(updates)
    assert applied >= 3

    # Verify persisted values
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT run_hash, validation_caution, validation_caution_metrics, trade_model_version FROM runs_extras"
        ).fetchall()
        got = {r[0]: (r[1], r[2], r[3]) for r in rows}

    assert got[run_a][0] == 1
    assert json.loads(got[run_a][1]) == ["permutation", "block_bootstrap"]
    assert got[run_a][2] == "2"

    assert got[run_b][0] == 0
    assert json.loads(got[run_b][1]) == []
    assert got[run_b][2] is None

    # When missing, fields remain NULL
    assert got[run_c][0] is None and got[run_c][1] is None and got[run_c][2] is None
