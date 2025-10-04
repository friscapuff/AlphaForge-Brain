"""Robustness scoring (T042).

Combines validation results and simple OOS stability placeholders into a
composite score. Weights are provisional; adjust via spec changes.
"""

from __future__ import annotations

from collections.abc import Sequence

from models.validation_result import ValidationResult


def robustness_score(
    validation: Sequence[ValidationResult], *, oos_consistency: float | None = None
) -> float:
    if not validation and oos_consistency is None:
        return 0.0
    # p-value contribution: average (higher is better here assuming two-sided > significance)
    p_values = [v.p_value for v in validation if v.p_value is not None]
    # Cast to float via explicit float division to avoid Any inference if list empty
    p_component: float = (
        (float(sum(p_values)) / float(len(p_values))) if p_values else 0.0
    )
    stability = oos_consistency or 0.0
    # Simple weighted sum (0..1 domain expected)
    return 0.6 * p_component + 0.4 * stability


def compute_robustness_score(
    p_value: float, extreme_tail_ratio: float, oos_consistency_score: float
) -> float:
    """Compute composite robustness score (alternate formula used in docs).

    Uses multiplicative weighting to penalize weakness in any component.
    Inputs are clamped to >=0; p_value inverted (1 - p) so lower p increases score.
    Returns a rounded float for deterministic hashing.
    """
    p_clamped = 0.0 if p_value < 0.0 else 1.0 if p_value > 1.0 else p_value
    evidence = 1.0 - p_clamped
    epsilon = 1e-9
    score: float = (
        (evidence + epsilon) ** 0.4
        * (extreme_tail_ratio + epsilon) ** 0.3
        * (oos_consistency_score + epsilon) ** 0.3
    )
    return float(round(score, 6))


__all__ = ["compute_robustness_score", "robustness_score"]
