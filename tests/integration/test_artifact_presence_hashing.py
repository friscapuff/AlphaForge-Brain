"""Integration test: artifact presence & hashing.

Validates that equity.parquet, trades.parquet (if trades exist), plots.png are written
and listed in manifest.json with non-empty sha256 & size. Uses create_or_get with
artifacts_base override (new parameter) to isolate outputs in tmp_path.
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
from integration.fixtures_manifest import artifact_hashes


@pytest.mark.parametrize("fast,slow", [(5,15)])
def test_artifact_presence_and_hashing(tmp_path: Path, fast: int, slow: int) -> None:
    # Synthesize a small deterministic dataset via orchestrator fallback (symbol TEST)
    start = "2024-01-01"
    end = "2024-01-03"  # few minutes synthesized per orchestrator logic
    cfg = RunConfig(
        symbol="TEST",
        timeframe="1m",
        start=start,
        end=end,
        indicators=[IndicatorSpec(name="sma", params={"window": fast}), IndicatorSpec(name="sma", params={"window": slow})],
        strategy=StrategySpec(name="dual_sma", params={"fast": fast, "slow": slow}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(slippage_bps=0, fee_bps=0),
    )
    reg = InMemoryRunRegistry()
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    run_hash, record, created = create_or_get(cfg, reg, seed=42, artifacts_base=artifacts_dir)
    assert created is True
    run_dir = artifacts_dir / run_hash
    assert run_dir.exists(), "run artifacts directory missing"

    # Core expected JSON artifacts always present
    for fname in ["summary.json", "metrics.json", "validation.json", "manifest.json"]:
        path = run_dir / fname
        assert path.exists(), f"missing core artifact {fname}"
        assert path.stat().st_size > 0, f"empty file {fname}"

    # Optional binary artifacts: equity.parquet, plots.png should exist (equity curve is always built)
    equity_path = run_dir / "equity.parquet"
    assert equity_path.exists(), "equity.parquet missing"
    assert equity_path.stat().st_size > 0

    plot_path = run_dir / "plots.png"
    assert plot_path.exists(), "plots.png missing"
    assert plot_path.stat().st_size > 0

    trades_path = run_dir / "trades.parquet"
    # trades may be empty if no strategy signals; still expect file only if trades occurred.
    # We treat absence as acceptable but if present must be non-empty size.
    if trades_path.exists():
        assert trades_path.stat().st_size > 0

    # Read manifest directly from run directory (fixture helper uses global artifacts base)
    manifest = json.loads((run_dir / "manifest.json").read_text("utf-8"))
    hashes = artifact_hashes(manifest)
    # Ensure listed artifacts include at least the core + equity + plot
    for required in ["summary.json", "metrics.json", "validation.json", "equity.parquet", "plots.png"]:
        assert required in hashes, f"{required} not listed in manifest files"
        assert len(hashes[required]) == 64, f"invalid sha256 length for {required}"

    # If trades file exists ensure in manifest
    if trades_path.exists():
        assert "trades.parquet" in hashes

    # Snapshot stability check: re-run same config -> created False and no new directory
    run_hash2, _record2, created2 = create_or_get(cfg, reg, seed=42, artifacts_base=artifacts_dir)
    assert created2 is False
    assert run_hash2 == run_hash

__all__ = ["test_artifact_presence_and_hashing"]
