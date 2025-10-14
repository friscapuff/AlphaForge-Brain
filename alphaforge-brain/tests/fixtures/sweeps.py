from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from models.parameter_definition import ParameterCollection

_SWEEP_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "data" / "sweeps"


def load_sweep_fixture(name: str = "dual_sma") -> dict[str, Any]:
    """Load a canonical sweep payload fixture from disk."""

    path = _SWEEP_FIXTURE_ROOT / f"{name}.json"
    if not path.exists():  # pragma: no cover - defensive guard for future fixtures
        raise FileNotFoundError(f"Unknown sweep fixture '{name}' at {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_parameter_collection(
    parameters: Mapping[str, Any] | None,
) -> ParameterCollection:
    """Construct a ParameterCollection from raw strategy parameters."""

    return ParameterCollection.from_raw(parameters)


def dual_sma_parameters() -> dict[str, Any]:
    """Return the raw strategy parameter mapping for the dual SMA sweep."""

    payload = load_sweep_fixture("dual_sma")
    strategy = payload.get("strategy", {})
    parameters = strategy.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("dual_sma fixture missing strategy parameters")
    return dict(parameters)


def dual_sma_parameter_collection(
    overrides: Mapping[str, Any] | None = None,
) -> ParameterCollection:
    """Build the canonical dual SMA ParameterCollection with optional overrides."""

    parameters = dual_sma_parameters()
    if overrides:
        parameters.update(overrides)
    return build_parameter_collection(parameters)


def dual_sma_parameter_grid(
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, tuple[Any, ...]]:
    """Return the normalized sweep grid for the dual SMA fixture."""

    collection = dual_sma_parameter_collection(overrides=overrides)
    return {definition.name: definition.unique_values for definition in collection}


def parameter_payload(collection: ParameterCollection) -> dict[str, Any]:
    """Return the canonical payload form for the provided collection."""

    return collection.as_payload()


def combination_count(collection: ParameterCollection) -> int:
    """Total number of unique parameter combinations represented by the collection."""

    return collection.combination_count


__all__ = [
    "build_parameter_collection",
    "combination_count",
    "dual_sma_parameter_collection",
    "dual_sma_parameter_grid",
    "dual_sma_parameters",
    "load_sweep_fixture",
    "parameter_payload",
]
