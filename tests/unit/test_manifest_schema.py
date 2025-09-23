from datetime import datetime, timezone

from src.models.cost_model_config import CostModelConfig
from src.models.dataset_snapshot import DatasetSnapshot
from src.models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from src.models.manifest import ArtifactDescriptor, RunManifest
from src.models.run_config import RunConfig
from src.models.strategy_config import StrategyConfig
from src.models.validation_config import ValidationConfig


def make_config() -> RunConfig:
    ds = DatasetSnapshot(
        path="/tmp/data.csv",
        data_hash="hash123",
        calendar_id="NYSE",
        bar_count=100,
    first_ts=datetime.now(timezone.utc),
    last_ts=datetime.now(timezone.utc),
        gap_count=0,
        holiday_gap_count=0,
        duplicate_count=0,
    )
    strat = StrategyConfig(id="strat", required_features=[], parameters={})
    exec_cfg = ExecutionConfig(fill_policy=FillPolicy.NEXT_BAR_OPEN, lot_size=1, rounding_mode=RoundingMode.ROUND)
    cost_cfg = CostModelConfig(slippage_bps=0, spread_pct=None, participation_rate=None, fee_bps=0, borrow_cost_bps=0)
    val_cfg = ValidationConfig(permutation_trials=0, seed=1, caution_p_threshold=0.1)
    return RunConfig(
        dataset=ds,
        features=[],
        strategy=strat,
        execution=exec_cfg,
        cost=cost_cfg,
        validation=val_cfg,
        walk_forward=None,
    )


def test_manifest_composite_hash_and_artifact_fields(freeze_time):
    artifacts = [
        ArtifactDescriptor(name="metrics.json", path="runs/x/metrics.json", content_hash="abc", mime_type="application/json"),
        ArtifactDescriptor(name="equity.parquet", path="runs/x/equity.parquet", content_hash="def", mime_type="application/octet-stream"),
    ]
    cfg = make_config()
    manifest = RunManifest.from_run_config("run123", cfg, artifacts)
    # created_at should be close to frozen time (allowing for model default executed inside factory)
    assert manifest.created_at.replace(tzinfo=freeze_time.now().tzinfo) == freeze_time.now()
    assert manifest.run_id == "run123"
    assert manifest.config_signature
    assert len(manifest.artifacts) == 2
    # Composite hash deterministic and recomputable
    recomputed = manifest.compute_composite_hash()
    assert recomputed == manifest.composite_hash
    # Changing order should not change composite hash since sort by name
    reversed_manifest = RunManifest(
        run_id="run123",
        config_signature=manifest.config_signature,
        artifacts=list(reversed(artifacts)),
        created_at=freeze_time.now(),
    )
    assert reversed_manifest.composite_hash == manifest.composite_hash
