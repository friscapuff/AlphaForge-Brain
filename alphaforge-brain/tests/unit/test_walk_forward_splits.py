from datetime import datetime, timezone

import pytest
from src.models.walk_forward_config import (
    WalkForwardConfig,
    WalkForwardOptimizationConfig,
    WalkForwardRobustnessConfig,
    WalkForwardSegmentConfig,
)
from src.services.walk_forward import choose_params, segment_boundaries

from tests.factories import walk_forward_variant


def config(train: int, test: int, warmup: int = 0) -> WalkForwardConfig:
    return WalkForwardConfig(
        segment=WalkForwardSegmentConfig(
            train_bars=train, test_bars=test, warmup_bars=warmup
        ),
        optimization=WalkForwardOptimizationConfig(
            enabled=True, param_grid={"a": [1, 2], "b": [10]}
        ),
        robustness=WalkForwardRobustnessConfig(compute=True),
    )


@pytest.mark.parametrize(
    "train,test,warmup,total",
    [
        (50, 10, 0, 150),
        (30, 5, 0, 90),
        (40, 10, 5, 160),
        (
            80,
            20,
            0,
            95,
        ),  # total smaller than two full strides => expect 0 or 1 depending on strict coverage
    ],
)
def test_segment_boundaries_stride_and_overlap(train, test, warmup, total):
    cfg = walk_forward_variant(train, test, warmup=warmup)
    bounds = segment_boundaries(datetime.now(timezone.utc), cfg, total_bars=total)
    # If total bars cannot satisfy a full train+test window, segmentation yields none; allow empty for this edge.
    if total < train + test:
        assert bounds == []
        return
    assert bounds, "Expected at least one segment"
    stride = train + test
    # First span length check (allow truncated last segment only if total < stride)
    first_len = bounds[0][1] - bounds[0][0]
    assert first_len == stride or (len(bounds) == 1 and first_len <= stride)
    # Monotonic and stride stepping by test bars for intermediate FULL segments
    for i in range(1, len(bounds)):
        assert bounds[i][0] - bounds[i - 1][0] == test
        seg_len = bounds[i][1] - bounds[i][0]
        # Last segment can be truncated if remaining bars insufficient
        if i < len(bounds) - 1:
            assert seg_len == stride
        else:
            assert 0 < seg_len <= stride
    # Within total
    assert bounds[-1][1] <= total
    # Expected count formula: number of start indices i where i + train + test <= total, stepping by test.
    expected = 0
    i = 0
    while i + stride <= total:
        expected += 1
        i += test
    assert len(bounds) == expected


def test_choose_params_deterministic_first_combo():
    cfg = config(30, 10)
    params = choose_params(cfg)
    # Keys sorted => a then b; first combo => a=1,b=10
    assert params == {"a": 1, "b": 10}
