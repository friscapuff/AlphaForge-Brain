"""Masters validation gating tests (US1/T006)."""

from __future__ import annotations

from domain.validation.masters.permutation_result import PermutationValidationResult
from models.run_validation_status import RunValidationStatus
from services.validation.aggregator import ValidationAggregator
from services.validation.status import determine_validation_status


def _permutation_result(p_value: float) -> PermutationValidationResult:
    return PermutationValidationResult(
        run_hash="RUN_HASH",
        segment_id="in_sample",
        p_value=p_value,
        effect_size=None,
        requested_permutations=1024,
        executed_permutations=1024,
        seed_root=123,
        histogram=None,
        artifact_path=None,
    )


def test_permutation_failure_marks_failed_validation() -> None:
    aggregator = ValidationAggregator(
        significance_threshold=0.05, leakage_threshold=0.1
    )
    aggregate = aggregator.aggregate(permutations=[_permutation_result(0.91)])

    status = determine_validation_status(aggregate)

    assert status is RunValidationStatus.FAILED_VALIDATION


def test_permutation_caution_marks_caution_status() -> None:
    aggregator = ValidationAggregator(
        significance_threshold=0.05, leakage_threshold=0.1
    )
    aggregate = aggregator.aggregate(permutations=[_permutation_result(0.08)])

    status = determine_validation_status(aggregate)

    assert status is RunValidationStatus.CAUTION


def test_permutation_success_marks_passed() -> None:
    aggregator = ValidationAggregator(
        significance_threshold=0.05, leakage_threshold=0.1
    )
    aggregate = aggregator.aggregate(permutations=[_permutation_result(0.01)])

    status = determine_validation_status(aggregate)

    assert status is RunValidationStatus.PASSED
