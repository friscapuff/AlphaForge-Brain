from __future__ import annotations

from decimal import Decimal

from models.parameter_definition import ParameterCollection
from services.sweeps.expander import expand_parameter_grid


def _combination_dicts(expansion):
    return [combo.as_dict() for combo in expansion.combinations]


def test_expand_parameter_grid_produces_deterministic_combinations() -> None:
    parameters = ParameterCollection.from_raw(
        {
            "fast": [5, 8],
            "slow": {"start": 30, "stop": 61, "step": 15},
        }
    )

    expansion = expand_parameter_grid(parameters)

    assert expansion.parameter_names == ("fast", "slow")
    assert expansion.cartesian_size == 6
    assert expansion.unique_count == 6
    assert _combination_dicts(expansion) == [
        {"fast": 5, "slow": 30},
        {"fast": 5, "slow": 45},
        {"fast": 5, "slow": 60},
        {"fast": 8, "slow": 30},
        {"fast": 8, "slow": 45},
        {"fast": 8, "slow": 60},
    ]


def test_expand_parameter_grid_deduplicates_overlapping_values() -> None:
    parameters = ParameterCollection.from_raw(
        {
            "threshold": {
                "mode": "list",
                "values": [Decimal("0.1000000"), "0.1000001", 0.1000002],
                "precision": 3,
            },
            "bias": [0, 0.0, Decimal("0")],
        }
    )

    expansion = expand_parameter_grid(parameters)

    assert expansion.cartesian_size == 1
    assert expansion.unique_count == 1
    assert _combination_dicts(expansion) == [
        {"threshold": 0.1, "bias": 0},
    ]


def test_expand_parameter_grid_supports_empty_collection() -> None:
    parameters = ParameterCollection.from_raw({})

    expansion = expand_parameter_grid(parameters)

    assert expansion.parameter_names == ()
    assert expansion.cartesian_size == 1
    assert expansion.unique_count == 1
    assert _combination_dicts(expansion) == [{}]
