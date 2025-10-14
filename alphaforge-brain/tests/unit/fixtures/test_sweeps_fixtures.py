from __future__ import annotations

from tests.fixtures import (
    build_parameter_collection,
    combination_count,
    dual_sma_parameter_collection,
    dual_sma_parameter_grid,
    dual_sma_parameters,
    load_sweep_fixture,
    parameter_payload,
)


def test_load_sweep_fixture_dual_sma() -> None:
    payload = load_sweep_fixture("dual_sma")

    assert payload["strategy"]["name"] == "dual_sma"
    assert "parameters" in payload["strategy"]


def test_dual_sma_parameter_collection_defaults() -> None:
    collection = dual_sma_parameter_collection()

    grid = dual_sma_parameter_grid()

    assert tuple(grid["fast"]) == (5, 8, 13)
    assert grid["slow"] == (30, 45, 60)
    assert collection.combination_count == 9
    assert combination_count(collection) == 9

    payload = parameter_payload(collection)
    assert payload["fast"]["mode"] == "list"
    assert payload["slow"]["mode"] == "range"


def test_dual_sma_parameter_collection_overrides() -> None:
    overrides = {"threshold": {"mode": "single", "value": 0.75}}
    collection = dual_sma_parameter_collection(overrides=overrides)

    threshold = next(defn for defn in collection if defn.name == "threshold")
    assert threshold.representative_value() == 0.75
    assert threshold.mode.value == "single"


def test_build_parameter_collection_from_mapping() -> None:
    parameters = {"alpha": [0.1, 0.2], "beta": {"start": 1, "stop": 4, "step": 2}}
    collection = build_parameter_collection(parameters)

    assert collection.combination_count == 4
    assert {definition.name for definition in collection} == {"alpha", "beta"}

    payload = parameter_payload(collection)
    assert payload["alpha"]["mode"] == "list"
    assert payload["beta"]["mode"] == "range"


def test_dual_sma_parameters_returns_mapping() -> None:
    params = dual_sma_parameters()

    assert set(params.keys()) == {"fast", "slow"}
    assert params["fast"]["values"] == [5, 8, 13]
