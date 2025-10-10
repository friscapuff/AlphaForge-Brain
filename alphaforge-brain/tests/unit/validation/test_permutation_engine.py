from __future__ import annotations

import json
from collections import Counter
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

import pytest

from tests.fixtures.validation import validation_fixtures

try:  # pragma: no cover - module intentionally absent until implementation phase
    _module = import_module("src.services.validation.masters_permutation")
except ImportError as exc:  # pragma: no cover - exercised via xfail path
    PermutationEngine: type[object] | None = None
    _IMPORT_ERROR: Exception | None = exc
else:  # pragma: no cover - future code path
    PermutationEngine = getattr(_module, "PermutationEngine", None)
    _IMPORT_ERROR = (
        None
        if PermutationEngine is not None
        else ImportError("PermutationEngine attribute missing")
    )


xfail_perm_engine = pytest.mark.xfail(
    reason="PermutationEngine deterministic batching not implemented",
    strict=False,
)


def _load_spec_payload() -> dict[str, Any]:
    payload_path = Path("spec_payload.json")
    if not payload_path.exists():
        pytest.skip("spec_payload.json missing; validation scaffolding incomplete")
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _optimizer_stub(
    recorder: list[tuple[str, int]]
) -> Callable[[str, int, dict[str, Any]], dict[str, Any]]:
    def _optimize(
        segment_id: str, seed: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        recorder.append((segment_id, seed))
        return {
            "risk_target": context.get("risk_target", 0.1),
            "lookback": 30 + (seed % 7),
        }

    return _optimize


@xfail_perm_engine
def test_permutation_engine_batches_are_deterministic_and_track_reoptimisation_hooks() -> (
    None
):
    if PermutationEngine is None:
        pytest.xfail(f"PermutationEngine module missing: {_IMPORT_ERROR}")

    fixture = validation_fixtures(permutation_trials=32)
    _load_spec_payload()  # ensure spec payload exists for parity with other tests

    optimizer_calls: list[tuple[str, int]] = []
    optimizer_hook = _optimizer_stub(optimizer_calls)

    engine = PermutationEngine(
        bars=fixture.bars,
        run_config=fixture.run_config,
        seed_bundle=fixture.seeds,
        optimizer_hook=optimizer_hook,
    )

    in_sample_result = engine.execute_segment("in_sample")
    assert in_sample_result.segment_id == "in_sample"
    assert in_sample_result.executed_permutations == 32
    assert in_sample_result.seed_root == fixture.seeds.seed_root

    histogram_summary = in_sample_result.histogram_summary
    assert isinstance(histogram_summary, dict)
    assert histogram_summary.keys() >= {"mean", "std_dev", "percentiles"}
    assert histogram_summary["percentiles"].keys() >= {"5", "50", "95"}

    optimizer_seeds = [
        seed for segment, seed in optimizer_calls if segment == "in_sample"
    ]
    assert optimizer_seeds == list(fixture.seeds.permutation[:32])

    rerun_result = engine.execute_segment("in_sample")
    assert rerun_result.histogram_summary == histogram_summary
    assert rerun_result.p_value == pytest.approx(in_sample_result.p_value, rel=1e-9)

    walk_forward_result = engine.execute_segment("walk_forward")
    assert walk_forward_result.segment_id == "walk_forward"
    assert walk_forward_result.executed_permutations == 32
    assert isinstance(walk_forward_result.histogram_summary, dict)

    coverage = Counter(seg for seg, _ in optimizer_calls)
    assert coverage["in_sample"] == in_sample_result.executed_permutations
    assert coverage["walk_forward"] == walk_forward_result.executed_permutations

    assert (
        walk_forward_result.reoptimised_params["lookback"]
        != in_sample_result.reoptimised_params["lookback"]
    )
