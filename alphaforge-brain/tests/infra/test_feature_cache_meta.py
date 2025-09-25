from __future__ import annotations

from pathlib import Path

import pandas as pd

from infra import config as _config
from infra.db import get_connection
from infra.persistence import init_run, record_feature_cache_artifact


def test_record_feature_cache_artifact_updates_manifest_and_table(
    tmp_path: Path, monkeypatch
) -> None:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "featuremeta.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "1" * 64
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

    # Create a tiny parquet artifact
    df = pd.DataFrame({"a": [1, 2, 3]})
    pq = tmp_path / "feat.parquet"
    df.to_parquet(pq, index=False)

    spec = {
        "candle_hash": "c" * 16,
        "engine_version": "v1",
        "indicators": ["sma:window=5"],
    }
    entry = record_feature_cache_artifact(
        run_hash=run_hash, parquet_path=pq, spec_json=spec, built_at_ms=10
    )

    assert entry["rows"] == 3
    assert entry["columns"] == 1
    assert entry["path"].endswith("feat.parquet")

    with get_connection() as conn:
        # Verify features_cache table row exists
        row = conn.execute(
            "SELECT spec_json, rows, columns, digest FROM features_cache WHERE meta_hash=?",
            (entry["meta_hash"],),
        ).fetchone()
        assert row is not None
        assert int(row["rows"]) == 3
        assert int(row["columns"]) == 1

        # Verify manifest_json updated with features_cache array containing the entry
        mrow = conn.execute(
            "SELECT manifest_json FROM runs WHERE run_hash=?", (run_hash,)
        ).fetchone()
        import json

        manifest = json.loads(mrow[0])
        feats = manifest.get("features_cache")
        assert isinstance(feats, list) and any(
            isinstance(e, dict) and e.get("meta_hash") == entry["meta_hash"]
            for e in feats
        )
