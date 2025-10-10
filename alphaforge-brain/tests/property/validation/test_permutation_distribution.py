from __future__ import annotations

from typing import Literal

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.services.validation.masters_permutation import PermutationEngine

from tests.fixtures.validation import validation_fixtures


@settings(max_examples=25, deadline=None, suppress_health_check=(HealthCheck.too_slow,))
@given(
    permutation_trials=st.integers(min_value=4, max_value=128),
    segment=st.sampled_from(("in_sample", "walk_forward")),
)
def test_histogram_counts_match_permutations(
    permutation_trials: int, segment: Literal["in_sample", "walk_forward"]
) -> None:
    fixture = validation_fixtures(permutation_trials=permutation_trials, bar_count=320)
    engine = PermutationEngine(
        bars=fixture.bars,
        run_config=fixture.run_config,
        seed_bundle=fixture.seeds,
    )

    result = engine.execute_segment(segment)

    summary = result.histogram_summary
    counts = summary.get("counts", [])
    bins = summary.get("bins")
    percentiles = summary.get("percentiles", {})

    assert isinstance(counts, list)
    assert isinstance(bins, int)
    assert len(counts) == bins
    assert sum(counts) == result.executed_permutations

    minimum = summary.get("min")
    maximum = summary.get("max")
    mean = summary.get("mean")

    assert isinstance(minimum, float)
    assert isinstance(maximum, float)
    assert isinstance(mean, float)
    assert minimum <= mean <= maximum

    p5 = percentiles.get("5")
    p50 = percentiles.get("50")
    p95 = percentiles.get("95")
    if all(isinstance(val, float) for val in (p5, p50, p95)):
        assert minimum <= p5 <= p50 <= p95 <= maximum

    assert 0.0 < result.p_value <= 1.0


@settings(max_examples=10, deadline=None, suppress_health_check=(HealthCheck.too_slow,))
@given(permutation_trials=st.integers(min_value=4, max_value=64))
def test_constant_return_histogram_collapses_to_single_bin(
    permutation_trials: int,
) -> None:
    fixture = validation_fixtures(permutation_trials=permutation_trials, bar_count=96)

    bars = fixture.bars.copy()
    constant_price = float(bars["close"].iloc[0])
    for column in ("open", "high", "low", "close"):
        bars[column] = constant_price
    bars["volume"] = np.ones(len(bars), dtype=float)

    engine = PermutationEngine(
        bars=bars,
        run_config=fixture.run_config,
        seed_bundle=fixture.seeds,
    )

    result = engine.execute_segment("in_sample")
    summary = result.histogram_summary
    counts = summary.get("counts", [])

    assert sum(counts) == result.executed_permutations
    assert counts[0] == result.executed_permutations
    assert all(count == 0 for count in counts[1:])

    minimum = summary.get("min")
    maximum = summary.get("max")
    assert minimum == pytest.approx(maximum)
    assert summary.get("std_dev") == 0.0
    assert result.effect_size == pytest.approx(0.0)
