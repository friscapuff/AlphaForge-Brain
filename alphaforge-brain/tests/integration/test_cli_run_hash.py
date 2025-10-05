from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner
from src.models.cost_model_config import CostModelConfig
from src.models.dataset_snapshot import DatasetSnapshot
from src.models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from src.models.feature_spec import FeatureSpec
from src.models.run_config import RunConfig
from src.models.strategy_config import StrategyConfig
from src.models.validation_config import ValidationConfig
from src.services.cli.run_hash import main as run_hash_cli
from src.services.manifest import collect_artifacts
from src.services.run_hash import compute_run_hash


def _make_config(seed: int = 1) -> RunConfig:
    ds = DatasetSnapshot(
        path="/tmp/data.csv",
        data_hash="hash123",
        calendar_id="NYSE",
        bar_count=100,
        first_ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_ts=datetime(2024, 1, 2, tzinfo=timezone.utc),
        gap_count=0,
        holiday_gap_count=0,
        duplicate_count=0,
    )
    strat = StrategyConfig(id="s", required_features=["ma"], parameters={"k": 1})
    exec_cfg = ExecutionConfig(
        fill_policy=FillPolicy.NEXT_BAR_OPEN,
        lot_size=1,
        rounding_mode=RoundingMode.ROUND,
    )
    cost_cfg = CostModelConfig(
        slippage_bps=0,
        spread_pct=None,
        participation_rate=None,
        fee_bps=0,
        borrow_cost_bps=0,
    )
    val_cfg = ValidationConfig(
        permutation_trials=10, seed=seed, caution_p_threshold=0.1
    )
    fs = FeatureSpec(
        name="ma", version="1", inputs=["close"], params={"w": 5}, shift_applied=1
    )
    return RunConfig(
        dataset=ds,
        features=[fs],
        strategy=strat,
        execution=exec_cfg,
        cost=cost_cfg,
        validation=val_cfg,
        walk_forward=None,
    )


@pytest.mark.integration
@pytest.mark.determinism
def test_cli_run_hash_matches_service(tmp_path: Path):
    cfg = _make_config(seed=7)
    cfg_path = tmp_path / "rc.json"
    cfg_path.write_text(json.dumps(cfg.model_dump(mode="json")), encoding="utf-8")

    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    p1.write_text("hello", encoding="utf-8")
    p2.write_text("world", encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(
        run_hash_cli, ["--config", str(cfg_path), str(p1), str(p2), "--quiet"]
    )
    assert res.exit_code == 0
    cli_hash = res.output.strip()

    svc_hash = compute_run_hash(cfg, collect_artifacts([p1, p2]))
    assert cli_hash == svc_hash


@pytest.mark.integration
@pytest.mark.determinism
def test_cli_run_hash_order_independent(tmp_path: Path):
    cfg = _make_config(seed=8)
    cfg_path = tmp_path / "rc.json"
    cfg_path.write_text(json.dumps(cfg.model_dump(mode="json")), encoding="utf-8")
    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    p1.write_text("hello", encoding="utf-8")
    p2.write_text("world", encoding="utf-8")

    runner = CliRunner()
    res1 = runner.invoke(
        run_hash_cli, ["--config", str(cfg_path), str(p1), str(p2), "--quiet"]
    )
    res2 = runner.invoke(
        run_hash_cli, ["--config", str(cfg_path), str(p2), str(p1), "--quiet"]
    )
    assert res1.exit_code == 0 and res2.exit_code == 0
    assert res1.output.strip() == res2.output.strip()


@pytest.mark.integration
@pytest.mark.determinism
def test_cli_run_hash_seed_sensitive(tmp_path: Path):
    cfg1 = _make_config(seed=1)
    cfg2 = _make_config(seed=2)
    cfg1_path = tmp_path / "rc1.json"
    cfg2_path = tmp_path / "rc2.json"
    cfg1_path.write_text(json.dumps(cfg1.model_dump(mode="json")), encoding="utf-8")
    cfg2_path.write_text(json.dumps(cfg2.model_dump(mode="json")), encoding="utf-8")

    p = tmp_path / "x.txt"
    p.write_text("data", encoding="utf-8")

    runner = CliRunner()
    res1 = runner.invoke(run_hash_cli, ["--config", str(cfg1_path), str(p), "--quiet"])
    res2 = runner.invoke(run_hash_cli, ["--config", str(cfg2_path), str(p), "--quiet"])
    assert res1.exit_code == 0 and res2.exit_code == 0
    assert res1.output.strip() != res2.output.strip()
