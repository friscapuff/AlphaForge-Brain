from __future__ import annotations

from pathlib import Path

import pandas as pd
from src.infra.artifacts_root import resolve_artifact_root
from src.lib.artifacts import artifact_index, write_equity, write_json, write_trades


def test_artifact_index_basic(tmp_path: Path) -> None:
    base = tmp_path / "af_artifacts"
    root = resolve_artifact_root(base)
    run_hash = "abc1234567deadbeef"  # synthetic deterministic hash
    # Create minimal artifacts
    eq = pd.DataFrame({"ts": [1, 2, 3], "equity": [100.0, 101.0, 102.5]})
    tr = pd.DataFrame({"id": [1], "pnl": [2.5]})
    write_equity(run_hash, eq, base_dir=root)
    write_trades(run_hash, tr, base_dir=root)
    write_json(run_hash, "summary.json", {"equity_final": 102.5}, base_dir=root)
    write_json(run_hash, "metrics.json", {"sharpe": 1.23}, base_dir=root)
    write_json(run_hash, "validation.json", {"p_value": 0.5}, base_dir=root)
    # Extra file should be ignored
    (root / run_hash / "notes.txt").write_text("ignore", encoding="utf-8")

    idx = artifact_index(run_hash, base_dir=root)
    names = [x["name"] for x in idx]
    # Deterministic ordering (sorted) and whitelist enforcement
    assert names == sorted(names)  # already sorted
    assert "notes.txt" not in names
    # Expected subset present
    for expected in [
        "summary.json",
        "metrics.json",
        "validation.json",
        "equity.parquet",
        "trades.parquet",
    ]:
        assert expected in names
    # Hashes look like hex and sizes positive
    for item in idx:
        assert len(item["sha256"]) == 64
        assert int(item["sha256"], 16) >= 0
        assert item["size"] > 0


def test_artifact_index_empty(tmp_path: Path) -> None:
    base = tmp_path / "af_artifacts"
    root = resolve_artifact_root(base)
    run_hash = "doesnotexist"
    assert artifact_index(run_hash, base_dir=root) == []
