from __future__ import annotations

from decimal import Decimal

import pytest
from models.parameter_definition import (
    ParameterCollection,
    ParameterDefinition,
    ParameterMode,
)
from services.sweeps.expander import expand_parameter_grid


def test_range_precision_rounds_expected_values() -> None:
    definition = ParameterDefinition.from_payload(
        name="threshold",
        payload={
            "mode": "range",
            "range": {"start": 0.0, "stop": 0.3000001, "step": 0.1},
            "precision": 3,
        },
    )

    assert definition.mode is ParameterMode.RANGE
    assert definition.unique_values == pytest.approx((0.0, 0.1, 0.2, 0.3))
    assert definition.unique_count == 4


def test_duplicate_combinations_deduplicated_after_rounding() -> None:
    parameters = ParameterCollection.from_raw(
        {
            "alpha": {
                "mode": "list",
                "values": [Decimal("0.1000"), "0.10000", 0.1],
                "precision": 4,
            },
            "beta": {
                "mode": "range",
                "range": {"start": 1, "stop": 1.3, "step": 0.1},
                "precision": 1,
            },
        }
    )

    expansion = expand_parameter_grid(parameters)

    alpha = parameters.get("alpha")
    assert alpha is not None
    assert alpha.unique_count == 1

    assert expansion.cartesian_size == 4
    assert expansion.unique_count == 4
    combos = [combo.as_dict() for combo in expansion.combinations]
    assert combos == [
        {"alpha": 0.1, "beta": 1.0},
        {"alpha": 0.1, "beta": 1.1},
        {"alpha": 0.1, "beta": 1.2},
        {"alpha": 0.1, "beta": 1.3},
    ]
