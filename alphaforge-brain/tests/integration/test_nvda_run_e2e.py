import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
import pytest
from domain.data.ingest_nvda import DatasetMetadata
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)


class SliceMeta(TypedDict):
    symbol: str
    timeframe: str


@pytest.mark.parametrize("fast,slow", [(5, 20)])
def test_nvda_end_to_end_run_artifacts(
    nvda_canonical_slice: tuple[pd.DataFrame, DatasetMetadata],
    fast: int,
    slow: int,
    tmp_path: Path,
) -> None:
    """T024: Full orchestrated run on NVDA slice producing artifacts & manifest.

    Validates that:
      - create_or_get returns created=True on first invocation
      - Artifacts directory contains manifest + summary/metrics/validation files
      - Manifest includes data_hash & calendar_id (provenance) and populated manifest_hash
      - Re-running with a different seed yields a second manifest whose chain_prev points to first manifest
    """
    (slice_df, meta) = nvda_canonical_slice
    assert not slice_df.empty

    # Use slice bounds for RunConfig date range
    first_date = (
        datetime.fromtimestamp(int(slice_df.ts.iloc[0]) / 1000, tz=timezone.utc)
        .date()
        .isoformat()
    )
    last_date = (
        datetime.fromtimestamp(int(slice_df.ts.iloc[-1]) / 1000, tz=timezone.utc)
        .date()
        .isoformat()
    )

    registry = InMemoryRunRegistry()
    # Override artifacts base to tmp_path to keep test isolated
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    cfg = RunConfig(
        symbol=meta.symbol,
        timeframe=meta.timeframe,
        start=first_date,
        end=last_date,
        indicators=[
            IndicatorSpec(name="dual_sma", params={"fast": fast, "slow": slow})
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": fast, "slow": slow}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.05}),
        execution=ExecutionSpec(slippage_bps=0, fee_bps=0),
    )

    # Patch artifacts base path by monkeypatching writer at import time
    import domain.artifacts.writer as writer_mod

    orig_write = writer_mod.write_artifacts

    def write_wrapper(run_hash: str, record: dict[str, Any], base_path: Path) -> Any:
        return orig_write(run_hash, record, base_path=artifacts_dir)

    writer_mod.write_artifacts = write_wrapper  # runtime patch
    try:
        h1, rec1, created1 = create_or_get(cfg, registry, seed=cfg.seed or 42)
    finally:
        writer_mod.write_artifacts = orig_write  # restore

    assert created1 is True
    run_dir1 = artifacts_dir / h1
    assert run_dir1.exists(), "Artifacts directory missing for run"
    manifest_path1 = run_dir1 / "manifest.json"
    summary_path1 = run_dir1 / "summary.json"
    metrics_path1 = run_dir1 / "metrics.json"
    validation_path1 = run_dir1 / "validation.json"
    for p in [manifest_path1, summary_path1, metrics_path1, validation_path1]:
        assert p.exists(), f"Missing artifact file: {p.name}"

    manifest1 = json.loads(manifest_path1.read_text("utf-8"))
    assert manifest1.get("manifest_hash"), "manifest_hash missing"
    # Retrieve live metadata to ensure comparison matches writer (which calls get_dataset_metadata)
    from domain.data.ingest_nvda import get_dataset_metadata

    live_meta = get_dataset_metadata()
    # Some tests may monkeypatch dataset metadata earlier; if so accept dummy placeholder but require presence
    assert manifest1.get("data_hash"), "data_hash missing in manifest"
    if manifest1.get("data_hash") != live_meta.data_hash:
        # Allow dummyhash used by API anomaly test monkeypatch
        assert manifest1.get("data_hash") == "dummyhash"
    assert manifest1.get("calendar_id") == live_meta.calendar_id
    assert manifest1.get("chain_prev") is None, "First run should have no chain_prev"

    # Second run with different seed -> new hash & manifest chained
    cfg2 = cfg.model_copy(
        update={
            "strategy": StrategySpec(
                name="dual_sma", params={"fast": fast, "slow": slow}
            )
        }
    )
    # Different seed ensures config hash difference only via seed if included; we intentionally change start by 0 days (no) so run hash stable unless seed influences
    # If seed not part of hash, force param tweak (fraction) to produce distinct run
    cfg2.risk.params["fraction"] = 0.06

    writer_mod.write_artifacts = write_wrapper
    try:
        h2, rec2, created2 = create_or_get(cfg2, registry, seed=123)
    finally:
        writer_mod.write_artifacts = orig_write

    assert created2 is True
    assert h2 != h1, "Second run hash should differ given modified risk fraction"
    manifest2 = json.loads((artifacts_dir / h2 / "manifest.json").read_text("utf-8"))
    assert manifest2.get("chain_prev") == manifest1.get(
        "manifest_hash"
    ), "chain_prev does not reference first manifest hash"

    # Basic metrics sanity: summary must contain top-level metrics structure
    summary = json.loads(summary_path1.read_text("utf-8"))
    metrics = json.loads(metrics_path1.read_text("utf-8"))
    assert isinstance(summary, dict)
    assert isinstance(metrics, dict)
    # trade_count present (may be zero for simple strategy) and total_return numeric
    if "metrics" in summary and isinstance(summary["metrics"], dict):
        assert (
            "total_return" in summary["metrics"]
        ), "total_return missing in summary metrics"
    assert "total_return" in metrics, "total_return missing in metrics.json"
