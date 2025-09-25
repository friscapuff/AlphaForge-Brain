from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import pytest
from domain.artifacts.retention import (
    ArtifactManifest,
    ArtifactRecord,
    ArtifactRetentionConfig,
    apply_retention,
)
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


class ArtifactType(
    str, Enum
):  # Minimal enum stub for compatibility with test fixture structure
    JSON = "JSON"


# Minimal RunConfig constructor helper consistent with earlier tests


def make_config(seed: int) -> RunConfig:
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        initial_equity=10000.0,
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
        strategy=StrategySpec(name="dual_sma", params={}),
        risk=RiskSpec(
            name="fixed_fraction", model="fixed_fraction", params={"fraction": 0.1}
        ),
        execution=ExecutionSpec(slippage_bps=1, fee_perc=0.0005),
        validation=ValidationSpec(
            permutation=None, block_bootstrap=None, monte_carlo=None, walk_forward=None
        ),
        seed=seed,
    )


def _manifest(tmp_path: Path, n: int = 5) -> ArtifactManifest:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    records: list[ArtifactRecord] = []
    for i in range(n):
        created = base.replace(day=min(28, 1 + i))
        fname = tmp_path / f"artifact_{i}.json"
        fname.write_text("{}", encoding="utf-8")
        records.append(
            ArtifactRecord(
                key=f"k{i}",
                type=ArtifactType.JSON,
                path=str(fname),
                created_at=created,
                bytes=2,
                meta={"idx": i},
                run_hash=f"h{i}",
            )
        )
    return ArtifactManifest(records=records)


def _cfg(keep: int | None, max_age_days: int | None) -> ArtifactRetentionConfig:
    return ArtifactRetentionConfig(keep_last=keep, max_age_days=max_age_days)


@pytest.mark.parametrize(
    "keep,max_age,expected",
    [
        (None, None, 5),
        (2, None, 2),
        (None, 10, 0),
        (3, 10, 0),
        (3, 1000, 3),
    ],
)
def test_apply_retention(
    tmp_path: Path, keep: int | None, max_age: int | None, expected: int
) -> None:
    manifest = _manifest(tmp_path)
    cfg = _cfg(keep, max_age)
    removed = apply_retention(
        cfg, manifest, now=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    # Validate removed file paths actually no longer exist
    for rec in removed:
        assert not Path(rec.path).exists()
    # Remaining count
    assert len(manifest.records) == expected


def test_apply_retention_idempotent(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    cfg = _cfg(keep=2, max_age_days=None)
    removed1 = apply_retention(cfg, manifest)
    removed2 = apply_retention(cfg, manifest)
    assert [r.key for r in removed1] == [r.key for r in removed2] == ["k0", "k1", "k2"]


def test_retention_prune_oldest_after_exceeding_limit() -> None:
    registry = InMemoryRunRegistry()

    # Insert 105 runs with monotonically increasing fake start_ts
    created_ids = []
    for i in range(105):
        cfg = make_config(seed=i)
        h, rec, created = create_or_get(cfg, registry, seed=i)
        assert created is True
        created_ids.append(h)

    # Because create_or_get integrates pruning, size should already be capped at 100
    assert len(registry.store) == 100

    from domain.run.retention import prune

    # Additional prune call should be a no-op now
    summary = prune(registry, limit=100)
    assert summary["removed"] == []
    assert summary["remaining"] == 100
    last_hash = created_ids[-1]
    assert last_hash in registry.store
