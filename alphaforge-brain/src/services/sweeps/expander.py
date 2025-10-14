from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

from models.parameter_definition import ParameterCollection, ParameterValue


@dataclass(frozen=True)
class SweepCombination:
    """Concrete assignment of parameter values for a single sweep run."""

    index: int
    values: tuple[tuple[str, ParameterValue], ...]

    def as_dict(self) -> dict[str, ParameterValue]:
        return {name: value for name, value in self.values}

    @property
    def parameters(self) -> tuple[tuple[str, ParameterValue], ...]:
        return self.values


@dataclass(frozen=True)
class SweepExpansion:
    """Deterministic expansion of a parameter collection into combinations."""

    parameter_names: tuple[str, ...]
    combinations: tuple[SweepCombination, ...]
    cartesian_size: int
    duplicate_count: int

    @property
    def unique_count(self) -> int:
        return len(self.combinations)

    def as_dicts(self) -> list[dict[str, ParameterValue]]:
        return [combo.as_dict() for combo in self.combinations]


def expand_parameter_grid(parameters: ParameterCollection) -> SweepExpansion:
    names: tuple[str, ...] = parameters.names
    value_sequences: list[tuple[ParameterValue, ...]] = [
        definition.unique_values for definition in parameters
    ]

    if not value_sequences:
        empty_combination = SweepCombination(index=0, values=())
        return SweepExpansion(
            parameter_names=names,
            combinations=(empty_combination,),
            cartesian_size=1,
            duplicate_count=0,
        )

    cartesian_size = 1
    for values in value_sequences:
        cartesian_size *= len(values)

    seen: set[tuple[tuple[str, ParameterValue], ...]] = set()
    ordered: list[SweepCombination] = []
    sequence_iterables: Iterable[tuple[ParameterValue, ...]] = product(*value_sequences)
    for combo_values in sequence_iterables:
        paired = tuple(zip(names, combo_values))
        if paired in seen:
            continue
        seen.add(paired)
        ordered.append(SweepCombination(index=len(ordered), values=paired))

    combinations = tuple(ordered)
    duplicate_count = max(cartesian_size - len(combinations), 0)

    return SweepExpansion(
        parameter_names=names,
        combinations=combinations,
        cartesian_size=cartesian_size,
        duplicate_count=duplicate_count,
    )


__all__ = [
    "SweepCombination",
    "SweepExpansion",
    "expand_parameter_grid",
]
