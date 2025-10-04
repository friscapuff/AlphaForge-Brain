from src.models.validation_result import ValidationResult
from src.services.robustness import robustness_score


def make_validation(p: float | None):
    return ValidationResult(
        metric_name="metric", observed_value=1.0, p_value=p, permutation_distribution=[]
    )


def test_weighted_sum_and_empty_behavior():
    vals = [make_validation(0.2), make_validation(0.4)]  # average p = 0.3
    score = robustness_score(vals, oos_consistency=0.5)
    # 0.6 * 0.3 + 0.4 * 0.5 = 0.18 + 0.2 = 0.38
    assert abs(score - 0.38) < 1e-12

    empty_score = robustness_score([], oos_consistency=None)
    assert empty_score == 0.0
