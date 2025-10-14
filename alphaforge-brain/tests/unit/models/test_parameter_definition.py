from __future__ import annotations

from decimal import Decimal

import pytest
from models.parameter_definition import (
    ParameterCollection,
    ParameterDefinition,
    ParameterMode,
)


def _dec(value: str) -> Decimal:
    return Decimal(value)


def test_parameter_definition_normalizes_range_sequence() -> None:
    definition = ParameterDefinition.from_payload(
        name="sma_window",
        payload=[{"start": 1, "stop": 4, "step": 1}],
    )

    assert definition.mode is ParameterMode.RANGE
    assert definition.unique_values == (1, 2, 3, 4)
    assert definition.unique_count == 4


def test_parameter_definition_normalizes_scalar_inputs() -> None:
    definition = ParameterDefinition.from_payload(
        name="threshold",
        payload={
            "mode": "list",
            "values": [1, Decimal("2"), "3.12345678901"],
            "precision": 6,
        },
    )

    assert definition.mode is ParameterMode.LIST
    values = definition.unique_values
    assert values[0] == 1
    assert values[1] == 2
    assert values[2] == pytest.approx(3.123457)
    assert definition.unique_count == 3


def test_parameter_definition_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        ParameterDefinition.from_payload(
            name="broken",
            payload=[{"start": 5, "stop": 1, "step": 1}],
        )


def test_parameter_collection_deduplicates_and_orders() -> None:
    definitions = ParameterCollection.from_raw(
        {
            "alpha": [1, 1, 2],
            "beta": {"start": 0.1, "stop": 0.4, "step": 0.1},
        }
    )

    names = [definition.name for definition in definitions]
    assert names == ["alpha", "beta"]

    alpha_values = next(
        defn for defn in definitions if defn.name == "alpha"
    ).unique_values
    beta_values = next(
        defn for defn in definitions if defn.name == "beta"
    ).unique_values

    assert alpha_values == (
        _dec("1.0000000000"),
        _dec("2.0000000000"),
    )
    assert beta_values == pytest.approx((0.1, 0.2, 0.3, 0.4))


@pytest.mark.parametrize(
    "payload",
    [
        42,
        {"mode": "single", "value": 42},
        {"value": 42},
    ],
)
def test_parameter_definition_scalar_permutations(payload: object) -> None:
    definition = ParameterDefinition.from_payload(name="alpha", payload=payload)

    assert definition.mode is ParameterMode.SINGLE
    assert definition.unique_values == (42,)


@pytest.mark.parametrize(
    "payload,expected",
    [
        ([1, 1, 2, 2], (1, 2)),
        (
            {
                "mode": "list",
                "values": [1, Decimal("1.0000"), "2", "2.0000000000"],
                "precision": 4,
            },
            (1, 2),
        ),
    ],
)
def test_parameter_definition_list_permutations(
    payload: object, expected: tuple[int, ...]
) -> None:
    definition = ParameterDefinition.from_payload(name="alpha", payload=payload)

    assert definition.mode is ParameterMode.LIST
    assert definition.unique_values == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"range": {"start": 0, "stop": 0.3, "step": 0.1}},
        {"mode": "range", "range": {"start": 0, "stop": 0.3, "step": 0.1}},
        [{"start": 0, "stop": 0.3, "step": 0.1}],
        {"min": 0, "max": 0.3, "step": 0.1},
    ],
)
def test_parameter_definition_range_permutations(payload: object) -> None:
    definition = ParameterDefinition.from_payload(name="window", payload=payload)

    assert definition.mode is ParameterMode.RANGE
    assert definition.unique_values == pytest.approx((0.0, 0.1, 0.2, 0.3))
