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


def test_migration_dry_run_and_apply_backfills_validation_and_version(
    tmp_path: Path, monkeypatch
) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "test.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    # Seed a run with manifest including validation caution and trade_model_version
    run_hash = "a" * 64
    manifest = {
        "schema_version": 1,
        "run_hash": run_hash,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "0" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "1" * 64},
        "validation_caution": True,
        "validation_caution_metrics": ["permutation"],
        "trade_model_version": "2",
    }
    init_run(
        run_hash=run_hash,
        created_at_ms=1,
        status="complete",
        config_json={},
        manifest_json=manifest,
        data_hash="0" * 64,
        seed_root=1,
        db_version=1,
        bootstrap_seed=1,
        walk_forward_spec=None,
    )

    # Load migration script and run dry-run
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "migrations"
        / "unify_trades.py"
    )
    mod = _load_script_module(script_path)
    updates = mod.discover_updates()
    assert any(u.run_hash == run_hash for u in updates)
    # Apply and verify rows written to runs_extras
    applied = mod.apply_updates(updates)
    assert applied >= 1

    with get_connection() as conn:
        row = conn.execute(
            "SELECT validation_caution, validation_caution_metrics, trade_model_version FROM runs_extras WHERE run_hash=?",
            (run_hash,),
        ).fetchone()
        assert row is not None
        vc = row[0]
        vcm = row[1]
        tmv = row[2]
        assert vc == 1
        assert json.loads(vcm) == ["permutation"]
        assert tmv == "2"


def test_migration_idempotency(tmp_path: Path, monkeypatch) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "test.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "b" * 64
    manifest = {
        "schema_version": 1,
        "run_hash": run_hash,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "0" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "2" * 64},
        # No validation or version present
    }
    init_run(
        run_hash=run_hash,
        created_at_ms=1,
        status="complete",
        config_json={},
        manifest_json=manifest,
        data_hash="0" * 64,
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
    updates1 = mod.discover_updates()
    applied1 = mod.apply_updates(updates1)
    updates2 = mod.discover_updates()
    applied2 = mod.apply_updates(updates2)
    # Applying twice should not error and should be idempotent in effect
    assert applied1 >= 1
    assert applied2 >= 1
    with get_connection() as conn:
        row = conn.execute(
            "SELECT validation_caution, validation_caution_metrics, trade_model_version FROM runs_extras WHERE run_hash=?",
            (run_hash,),
        ).fetchone()
        assert row is not None
        # All remain NULL since no fields provided
        assert row[0] is None and row[1] is None and row[2] is None
