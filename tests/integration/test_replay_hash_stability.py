"""Replay Stability Test

Asserts that re-running create_or_get with an identical RunConfig, identical seed,
identical dataset provenance, and clean registry produces:
    - created flag False on second invocation (cache hit)
    - identical manifest.json contents (byte-for-byte) OR if not re-written, existing unchanged
    - identical per-artifact sha256 hashes for summary.json, metrics.json, validation.json,
        equity.parquet, plots.png (and trades.parquet if present)

This enforces the determinism / reproducibility constitutional requirement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)


@pytest.mark.parametrize("fast,slow", [(5,15)])
def test_replay_hash_stability(tmp_path: Path, fast: int, slow: int) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    cfg = RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-03",
        indicators=[
            IndicatorSpec(name="sma", params={"window": fast}),
            IndicatorSpec(name="sma", params={"window": slow}),
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": fast, "slow": slow}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(slippage_bps=0, fee_bps=0),
    )

    registry = InMemoryRunRegistry()
    seed = 42

    run_hash1, record1, created1 = create_or_get(cfg, registry, seed=seed, artifacts_base=artifacts_dir)
    assert created1 is True
    run_dir1 = artifacts_dir / run_hash1
    manifest_path1 = run_dir1 / "manifest.json"
    manifest1 = json.loads(manifest_path1.read_text("utf-8"))

    # Capture artifact hashes from manifest1
    hashes1 = {f["name"]: f["sha256"] for f in manifest1["files"]}

    # Replay with identical config+seed
    run_hash2, record2, created2 = create_or_get(cfg, registry, seed=seed, artifacts_base=artifacts_dir)
    assert created2 is False  # cache hit
    assert run_hash2 == run_hash1

    # Reload manifest (should be unchanged on disk)
    manifest2 = json.loads(manifest_path1.read_text("utf-8"))
    hashes2 = {f["name"]: f["sha256"] for f in manifest2["files"]}

    assert manifest1 == manifest2, "Manifest mutated between identical replays"

    # Ensure stable hashes for required artifacts
    required = ["summary.json", "metrics.json", "validation.json", "equity.parquet", "plots.png"]
    for name in required:
        assert name in hashes1, f"{name} missing in first manifest"
        assert name in hashes2, f"{name} missing in second manifest"
        assert hashes1[name] == hashes2[name], f"Hash drift for {name}"

    # Trades (optional) if present must also be stable
    if "trades.parquet" in hashes1 or "trades.parquet" in hashes2:
        assert "trades.parquet" in hashes1 and "trades.parquet" in hashes2
        assert hashes1["trades.parquet"] == hashes2["trades.parquet"], "Hash drift for trades.parquet"

__all__ = ["test_replay_hash_stability"]
