"""Walk-Forward Segmentation & Param Selection Integration (T015)

Validates that walk-forward segment boundary construction and deterministic
parameter selection behave per spec:
 - Segments advance by test_bars (rolling) not full stride
 - Each segment covers train_bars + test_bars total span
 - Last partial segment (insufficient remaining bars) is discarded
 - choose_params deterministically returns first lexicographic param grid combo
 - Warmup bars are not yet applied to exclusion logic (future FR) but config accepted
 - Edge case: insufficient bars for a single segment yields empty list
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from models.walk_forward_config import (
    WalkForwardConfig,
    WalkForwardOptimizationConfig,
    WalkForwardRobustnessConfig,
    WalkForwardSegmentConfig,
)
from services.walk_forward import choose_params, segment_boundaries


def _wf_cfg(train: int, test: int, warmup: int = 0) -> WalkForwardConfig:
    return WalkForwardConfig(
        segment=WalkForwardSegmentConfig(
            train_bars=train, test_bars=test, warmup_bars=warmup
        ),
        optimization=WalkForwardOptimizationConfig(
            enabled=True,
            param_grid={
                "fast": [10, 20],
                "slow": [50, 60],
            },
        ),
        robustness=WalkForwardRobustnessConfig(compute=True),
    )


def test_walk_forward_segment_boundaries_basic() -> None:  # T015a
    cfg = _wf_cfg(train=100, test=20)
    total_bars = 400
    bounds = segment_boundaries(
        datetime(2024, 1, 1, tzinfo=timezone.utc), cfg, total_bars
    )
    # Expected progression: start at 0, stride = 120, advance index by test (20)
    # while index + train + test <= total => last index satisfying i+120 <=400 -> i<=280
    # i sequence: 0,20,40,60,80,100,120,140,160,180,200,220,240,260,280 (15 segments)
    assert len(bounds) == 15
    # First and last checks
    assert bounds[0] == (0, 120)
    assert bounds[-1] == (280, 400)
    # Overlap pattern: consecutive starts differ by test size
    starts = [b[0] for b in bounds]
    diffs = [s2 - s1 for s1, s2 in zip(starts, starts[1:])]
    assert all(d == 20 for d in diffs)
    # Span length constant
    lengths = [e - s for s, e in bounds]
    assert set(lengths) == {120}


def test_walk_forward_segment_bounds_insufficient() -> None:  # T015b
    cfg = _wf_cfg(train=50, test=25)
    # Need at least 75 bars; provide fewer
    total_bars = 60
    bounds = segment_boundaries(
        datetime(2024, 1, 1, tzinfo=timezone.utc), cfg, total_bars
    )
    assert bounds == []


def test_walk_forward_choose_params_deterministic() -> None:  # T015c
    cfg = _wf_cfg(train=80, test=20)
    params = choose_params(cfg)
    # Keys sorted lexicographically => fast, slow -> first combo (10,50)
    assert params == {"fast": 10, "slow": 50}
    # Determinism
    assert choose_params(cfg) == params


def test_walk_forward_choose_params_disabled() -> None:  # T015d
    cfg = WalkForwardConfig(
        segment=WalkForwardSegmentConfig(train_bars=60, test_bars=20, warmup_bars=0),
        optimization=WalkForwardOptimizationConfig(enabled=False, param_grid={}),
        robustness=WalkForwardRobustnessConfig(compute=True),
    )
    assert choose_params(cfg) == {}


def test_walk_forward_warmup_validation() -> None:  # T015e
    # warmup < train enforced
    _ = _wf_cfg(train=40, test=10, warmup=5)
    with pytest.raises(ValueError):
        WalkForwardSegmentConfig(train_bars=10, test_bars=5, warmup_bars=10)


__all__ = [
    "test_walk_forward_choose_params_deterministic",
    "test_walk_forward_choose_params_disabled",
    "test_walk_forward_segment_boundaries_basic",
    "test_walk_forward_segment_bounds_insufficient",
    "test_walk_forward_warmup_validation",
]
