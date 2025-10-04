from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from infra import config as _config
from infra.persistence import init_run


def _load_script_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("unify_trades", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_t091_migration_writes_json_report_and_schema(
    tmp_path: Path, monkeypatch
) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "t091.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    # Seed a pair of runs (one with caution/version fields, one without)
    run_a = "c" * 64
    run_b = "d" * 64
    man_a = {
        "schema_version": 1,
        "run_hash": run_a,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "0" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "a" * 64},
        "validation_caution": True,
        "validation_caution_metrics": ["permutation"],
        "trade_model_version": "2",
    }
    man_b = {
        "schema_version": 1,
        "run_hash": run_b,
        "db_version": 1,
        "created_at": 1,
        "updated_at": 1,
        "status": "complete",
        "data_hash": "f" * 64,
        "seed_root": 1,
        "provenance": {"manifest_content_hash": "b" * 64},
    }
    for rh, m in ((run_a, man_a), (run_b, man_b)):
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

    # Execute script main() in dry-run mode (default) with an output path
    out_path = tmp_path / "artifacts" / "migration" / "unified_trades_report.json"
    argv_backup = sys.argv[:]
    try:
        sys.argv = [str(script_path), "--output", str(out_path)]
        rc = mod.main()
    finally:
        sys.argv = argv_backup
    assert rc == 0

    # File exists and contains expected schema
    assert out_path.exists()
    data = json.loads(out_path.read_text("utf-8"))
    assert set(data.keys()) == {"dry_run", "total_runs", "planned_updates"}
    assert data["dry_run"] is True
    assert isinstance(data["total_runs"], int) and data["total_runs"] == 2
    assert (
        isinstance(data["planned_updates"], list) and len(data["planned_updates"]) == 2
    )

    # Validate an element shape and types; locate seeded run_a
    item = next(u for u in data["planned_updates"] if u["run_hash"] == run_a)
    assert set(item.keys()) == {
        "run_hash",
        "validation_caution",
        "validation_caution_metrics",
        "trade_model_version",
    }
    assert item["validation_caution"] in (0, 1, None)
    assert item["validation_caution"] == 1
    assert item["validation_caution_metrics"] == ["permutation"]
    assert item["trade_model_version"] == "2"
