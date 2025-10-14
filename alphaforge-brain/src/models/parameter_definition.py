"""Parameter normalization helpers for deterministic sweep expansion.

Implements FR-001/FR-002 prerequisites by providing a canonical representation of
strategy parameter definitions before they are expanded into concrete
combinations. The model accepts single values, explicit lists, or numeric ranges
and exposes helpers to derive normalized, deduplicated value sequences.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from enum import Enum
from typing import Any, Iterable, Iterator, Mapping, Sequence, cast, overload

from pydantic import Field, model_validator

from .base import BaseModelStrict

ParameterValue = int | float | str

_DEFAULT_PRECISION = 6


class ParameterMode(str, Enum):
    """Supported sweep parameter input styles."""

    SINGLE = "single"
    LIST = "list"
    RANGE = "range"


class ParameterDefinitionError(ValueError):
    """Raised when parameter definitions cannot be normalized."""


class ParameterRange(BaseModelStrict):
    """Numeric sweep range specification (inclusive start, exclusive stop)."""

    start: float | int
    stop: float | int
    step: float | int = Field(gt=0)

    @model_validator(mode="after")
    def _validate_bounds(self) -> ParameterRange:
        start_num = float(self.start)
        stop_num = float(self.stop)
        step_num = float(self.step)
        if start_num >= stop_num:
            raise ValueError("range start must be < stop")
        if step_num <= 0:
            raise ValueError("range step must be > 0")
        if step_num > (stop_num - start_num):
            raise ValueError("range step exceeds span")
        return self

    def iter_values(self, precision: int) -> Iterator[ParameterValue]:
        """Yield deterministic numeric values honouring precision settings."""

        quant = _decimal_quantizer(precision)
        start_d = Decimal(str(self.start))
        stop_d = Decimal(str(self.stop))
        step_d = Decimal(str(self.step))

        index = 0
        current = start_d
        while current < stop_d:
            quantized = current.quantize(quant, rounding=ROUND_HALF_EVEN)
            yield _coerce_decimal_output(quantized)
            index += 1
            current = start_d + (step_d * index)
        # Append stop if the final increment lands exactly on it
        if current == stop_d:
            quantized = current.quantize(quant, rounding=ROUND_HALF_EVEN)
            yield _coerce_decimal_output(quantized)


class ParameterDefinition(BaseModelStrict):
    """Canonical representation for a sweep parameter."""

    name: str
    mode: ParameterMode
    value: ParameterValue | None = None
    values: Sequence[ParameterValue] | None = None
    range: ParameterRange | None = None
    precision: int | None = Field(default=_DEFAULT_PRECISION, ge=0, le=9)

    @model_validator(mode="after")
    def _validate_payload(self) -> ParameterDefinition:
        has_value = self.value is not None
        has_values = bool(self.values)
        has_range = self.range is not None
        provided = sum(int(flag) for flag in (has_value, has_values, has_range))
        if provided != 1:
            raise ValueError("Exactly one of value, values, or range must be supplied")
        if self.mode is ParameterMode.SINGLE and not has_value:
            raise ValueError("Single mode requires `value`")
        if self.mode is ParameterMode.LIST and not has_values:
            raise ValueError("List mode requires `values`")
        if self.mode is ParameterMode.RANGE and not has_range:
            raise ValueError("Range mode requires `range`")
        return self

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def normalized_values(self) -> list[ParameterValue]:
        """Return deterministic value ordering after validation & dedupe."""

        precision = self.precision if self.precision is not None else _DEFAULT_PRECISION

        if self.mode is ParameterMode.SINGLE:
            assert self.value is not None  # validated above
            normalized = [_normalize_scalar(self.value, precision)]
        elif self.mode is ParameterMode.LIST:
            assert self.values is not None
            normalized = [_normalize_scalar(v, precision) for v in self.values]
        else:  # RANGE
            assert self.range is not None
            normalized = list(self.range.iter_values(precision))

        deduped = list(_dedupe_preserving_order(normalized))
        if not deduped:
            raise ParameterDefinitionError(
                f"Parameter '{self.name}' produced zero combinations"
            )
        return deduped

    @property
    def unique_values(self) -> tuple[ParameterValue, ...]:
        return tuple(self.normalized_values())

    @property
    def unique_count(self) -> int:
        return len(self.unique_values)

    def representative_value(self) -> ParameterValue:
        """Return the first normalized value for legacy single-run paths."""

        return self.normalized_values()[0]

    def as_payload(self) -> dict[str, Any]:
        """Return canonical dict representation for telemetry/manifests."""

        payload: dict[str, Any] = {
            "name": self.name,
            "mode": self.mode.value,
            "precision": self.precision,
        }
        if self.mode is ParameterMode.SINGLE:
            payload["value"] = self.value
        elif self.mode is ParameterMode.LIST:
            payload["values"] = list(self.values or [])
        else:
            payload["range"] = self.range.model_dump() if self.range else None
        return payload

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_payload(cls, name: str, payload: Any) -> ParameterDefinition:
        """Coerce arbitrary payload forms into a validated definition."""

        if isinstance(payload, ParameterDefinition):
            return payload
        if isinstance(payload, Mapping):
            data = dict(payload)
            range_payload: Mapping[str, Any] | None = None
            if "mode" in data:
                mode = ParameterMode(data["mode"])
                if mode is ParameterMode.RANGE:
                    raw_range = data.get("range")
                    if isinstance(raw_range, Mapping):
                        range_payload = raw_range
            elif "range" in data:
                mode = ParameterMode.RANGE
                raw_range = data["range"]
                if isinstance(raw_range, Mapping):
                    range_payload = raw_range
            elif {"start", "stop"}.issubset(data) or {"min", "max"}.issubset(data):
                mode = ParameterMode.RANGE
                range_payload = data
            elif "values" in data:
                mode = ParameterMode.LIST
            else:
                mode = ParameterMode.SINGLE

            precision = data.get("precision")
            raw_value = data.get("value")
            raw_values = data.get("values")

            value = cast(ParameterValue | None, raw_value)
            values = (
                cast(Sequence[ParameterValue], raw_values)
                if isinstance(raw_values, Sequence)
                and not isinstance(raw_values, (str, bytes))
                else None
            )

            if range_payload is not None and mode is ParameterMode.RANGE:
                range_payload_dict = dict(range_payload)
                if {"min", "max"}.issubset(range_payload_dict):
                    range_payload_dict.setdefault(
                        "start", range_payload_dict.pop("min")
                    )
                    range_payload_dict.setdefault("stop", range_payload_dict.pop("max"))
                param_range = ParameterRange.model_validate(range_payload_dict)
            else:
                param_range = None
                if mode is ParameterMode.SINGLE and value is None and values is None:
                    raise ParameterDefinitionError(
                        "Single parameter payload must include 'value' or 'values'"
                    )
            range_obj = param_range if param_range is not None else None
            return cls(
                name=name,
                mode=mode,
                value=value,
                values=values,
                range=range_obj,
                precision=precision,
            )
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
            seq_payload = list(payload)
            if len(seq_payload) == 1 and isinstance(seq_payload[0], Mapping):
                range_payload = dict(seq_payload[0])
                if {"min", "max"}.issubset(range_payload):
                    range_payload.setdefault("start", range_payload.pop("min"))
                    range_payload.setdefault("stop", range_payload.pop("max"))
                if {"start", "stop"}.issubset(range_payload):
                    return cls(
                        name=name,
                        mode=ParameterMode.RANGE,
                        range=ParameterRange.model_validate(range_payload),
                    )
            return cls(name=name, mode=ParameterMode.LIST, values=seq_payload)
        # Everything else treated as a scalar value
        return cls(name=name, mode=ParameterMode.SINGLE, value=payload)

    @classmethod
    def parse_parameters(
        cls, payload: Mapping[str, Any] | None
    ) -> dict[str, ParameterDefinition]:
        if not payload:
            return {}
        definitions: dict[str, ParameterDefinition] = {}
        for name, value in payload.items():
            definitions[name] = cls.from_payload(name, value)
        return definitions


class ParameterCollection(Sequence[ParameterDefinition]):
    """Ordered container of parameter definitions with helper utilities."""

    def __init__(self, definitions: Iterable[ParameterDefinition]):
        items: list[ParameterDefinition] = []
        seen: set[str] = set()
        for definition in definitions:
            if definition.name in seen:
                continue
            seen.add(definition.name)
            items.append(definition)
        self._items = tuple(items)

    def __iter__(self) -> Iterator[ParameterDefinition]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @overload
    def __getitem__(self, index: int) -> ParameterDefinition: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[ParameterDefinition, ...]: ...

    def __getitem__(
        self, index: int | slice
    ) -> ParameterDefinition | tuple[ParameterDefinition, ...]:
        return self._items[index]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(definition.name for definition in self._items)

    def get(self, name: str) -> ParameterDefinition | None:
        for definition in self._items:
            if definition.name == name:
                return definition
        return None

    @property
    def combination_count(self) -> int:
        total = 1
        for definition in self._items:
            total *= max(1, definition.unique_count)
        return total

    def as_payload(self) -> dict[str, Any]:
        return {definition.name: definition.as_payload() for definition in self._items}

    @classmethod
    def from_raw(
        cls, payload: Mapping[str, Any] | Iterable[Any] | None
    ) -> ParameterCollection:
        if payload is None:
            return cls([])
        if isinstance(payload, Mapping):
            return cls(
                ParameterDefinition.from_payload(name, value)
                for name, value in payload.items()
            )

        definitions: list[ParameterDefinition] = []
        for entry in payload:
            if isinstance(entry, ParameterDefinition):
                definitions.append(entry)
                continue
            if isinstance(entry, Mapping):
                if "name" not in entry:
                    raise ParameterDefinitionError(
                        "Parameter entry missing 'name' field"
                    )
                name = str(entry["name"])
                rest = {k: v for k, v in entry.items() if k != "name"}
                payload_value: Any
                if rest:
                    payload_value = rest
                elif "value" in entry:
                    payload_value = entry["value"]
                else:
                    payload_value = None
                definitions.append(
                    ParameterDefinition.from_payload(name, payload_value)
                )
                continue
            raise ParameterDefinitionError(
                f"Unsupported parameter collection entry type: {type(entry)!r}"
            )
        return cls(definitions)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _normalize_scalar(value: ParameterValue, precision: int) -> ParameterValue:
    if isinstance(value, bool):
        # Preserve bools even though they are ints in Python
        return value
    quant = _decimal_quantizer(precision)
    if isinstance(value, Decimal):
        return _coerce_decimal_output(value.quantize(quant, rounding=ROUND_HALF_EVEN))
    if isinstance(value, (int, float)):
        dec_value = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_EVEN)
        return _coerce_decimal_output(dec_value)
    if isinstance(value, str):
        try:
            dec_value = Decimal(value).quantize(quant, rounding=ROUND_HALF_EVEN)
        except (InvalidOperation, ValueError):
            return value
        return _coerce_decimal_output(dec_value)
    return value


def _dedupe_preserving_order(
    values: Iterable[ParameterValue],
) -> Iterable[ParameterValue]:
    seen: set[tuple[type[Any], ParameterValue]] = set()
    for value in values:
        key = (type(value), value)
        if key in seen:
            continue
        seen.add(key)
        yield value


def _decimal_quantizer(precision: int) -> Decimal:
    if precision <= 0:
        return Decimal("1")
    return Decimal("1").scaleb(-precision)


def _coerce_decimal_output(value: Decimal) -> ParameterValue:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


__all__ = [
    "ParameterDefinition",
    "ParameterDefinitionError",
    "ParameterMode",
    "ParameterRange",
    "ParameterCollection",
]
