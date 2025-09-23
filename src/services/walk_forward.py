"""Walk-forward segmentation & optimization stub (T041).

Creates segment boundaries based on config; parameter optimization currently
selects first grid combination deterministically.
"""

from __future__ import annotations

from datetime import datetime
from itertools import product

from models.walk_forward_config import WalkForwardConfig


def segment_boundaries(start: datetime, config: WalkForwardConfig, total_bars: int) -> list[tuple[int, int]]:
    seg = config.segment
    stride = seg.train_bars + seg.test_bars
    bounds: list[tuple[int, int]] = []
    index = 0
    while index + seg.train_bars + seg.test_bars <= total_bars:
        bounds.append((index, index + stride))
        index += seg.test_bars  # rolling forward by test window
    return bounds


def choose_params(config: WalkForwardConfig) -> dict[str, int | float | str]:
    if not config.optimization.enabled:
        return {}
    grid = config.optimization.param_grid
    # Deterministic first combo
    keys = sorted(grid.keys())
    combos = product(*[grid[k] for k in keys])
    first = next(combos, None)
    if first is None:
        return {}
    return {k: v for k, v in zip(keys, first)}

__all__ = ["choose_params", "segment_boundaries"]
