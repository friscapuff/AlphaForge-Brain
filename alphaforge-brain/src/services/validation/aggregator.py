from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from domain.validation.masters.bias_adjustment import SharpeBiasAdjustment
from domain.validation.masters.cross_validation_models import CrossValidationSummary
from domain.validation.masters.permutation_result import PermutationValidationResult
from domain.validation.realism.report import ExecutionRealismReport


@dataclass(slots=True)
class ValidationAggregate:
    validation_significance: str
    failed_checks: tuple[str, ...]
    caution_checks: tuple[str, ...]
    metadata: Mapping[str, object]


class ValidationAggregator:
    """Combine Masters validation modules into a single gating decision."""

    def __init__(
        self,
        *,
        significance_threshold: float,
        leakage_threshold: float,
    ) -> None:
        self._significance_threshold = float(max(significance_threshold, 1e-9))
        self._leakage_threshold = float(max(leakage_threshold, 0.0))
        self._permutation_fail_threshold = max(self._significance_threshold * 10.0, 0.5)

    def aggregate(
        self,
        *,
        permutations: Iterable[PermutationValidationResult] = (),
        bias_adjustment: SharpeBiasAdjustment | None = None,
        cross_validation: CrossValidationSummary | None = None,
        realism: ExecutionRealismReport | None = None,
    ) -> ValidationAggregate:
        failed: set[str] = set()
        caution: set[str] = set()

        permutation_outcomes = list(permutations)
        worst_p_value: float | None = None
        permutation_shortfalls: list[dict[str, int | str]] = []
        permutation_fallbacks: list[dict[str, str]] = []
        if permutation_outcomes:
            for outcome in permutation_outcomes:
                if outcome.p_value is not None:
                    worst_p_value = (
                        outcome.p_value
                        if worst_p_value is None
                        else max(worst_p_value, outcome.p_value)
                    )
                if outcome.executed_permutations < outcome.requested_permutations:
                    permutation_shortfalls.append(
                        {
                            "segment_id": outcome.segment_id,
                            "requested": outcome.requested_permutations,
                            "executed": outcome.executed_permutations,
                        }
                    )
                if outcome.fallback_reason:
                    permutation_fallbacks.append(
                        {
                            "segment_id": outcome.segment_id,
                            "reason": outcome.fallback_reason,
                        }
                    )
            if (
                worst_p_value is not None
                and worst_p_value > self._significance_threshold
            ):
                caution.add("permutation_significance")
            if (
                worst_p_value is not None
                and worst_p_value >= self._permutation_fail_threshold
            ):
                failed.add("permutation_significance")
            if permutation_shortfalls:
                caution.add("permutation_sampling")
            if permutation_fallbacks:
                caution.add("permutation_fallback")

        if bias_adjustment is not None:
            if bias_adjustment.bias_flag:
                failed.add("bias_adjustment")
            elif bias_adjustment.status != "pass":
                caution.add("bias_adjustment")

        if cross_validation is not None:
            if cross_validation.bias_flag:
                failed.add("cross_validation")
            elif (
                cross_validation.leakage_score is not None
                and cross_validation.leakage_score > self._leakage_threshold
            ):
                caution.add("cross_validation_leakage")

        if realism is not None:
            if realism.status == "fail":
                failed.add("execution_realism")
            elif realism.status == "caution":
                caution.add("execution_realism")

        validation_significance = "pass"
        if failed:
            validation_significance = "fail"
        elif caution:
            validation_significance = "caution"

        metadata: dict[str, object] = {
            "significance_threshold": self._significance_threshold,
            "leakage_threshold": self._leakage_threshold,
            "permutation_segments": [
                result.segment_id for result in permutation_outcomes
            ],
        }
        if worst_p_value is not None:
            metadata["max_p_value"] = worst_p_value
        if permutation_shortfalls:
            metadata["permutation_shortfalls"] = permutation_shortfalls
        if permutation_fallbacks:
            metadata["permutation_fallbacks"] = permutation_fallbacks
        if cross_validation is not None:
            metadata["cross_validation_mode"] = cross_validation.mode.value
            metadata["leakage_score"] = cross_validation.leakage_score
            metadata["cross_validation_bias_flag"] = cross_validation.bias_flag
        if bias_adjustment is not None:
            metadata["cscv_adjusted_sharpe"] = bias_adjustment.cscv_adjusted_sharpe
        if realism is not None:
            metadata["realism_status"] = realism.status

        return ValidationAggregate(
            validation_significance=validation_significance,
            failed_checks=tuple(sorted(failed)),
            caution_checks=tuple(sorted(caution)),
            metadata=metadata,
        )


__all__ = ["ValidationAggregate", "ValidationAggregator"]
