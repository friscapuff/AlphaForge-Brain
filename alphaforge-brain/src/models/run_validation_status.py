"""Canonical run validation status definitions."""

from __future__ import annotations

from enum import Enum
from typing import Iterator, Union

__all__ = [
    "RunValidationStatus",
    "coerce_validation_status",
    "is_failed_validation",
    "is_promotable",
    "requires_governance_review",
    "all_statuses",
]


class RunValidationStatus(str, Enum):
    """Enumeration describing validation outcomes for orchestrated runs."""

    PASSED = "PASSED"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    CAUTION = "CAUTION"

    def is_failed(self) -> bool:
        """Return ``True`` when the run represents a hard validation failure."""

        return self is RunValidationStatus.FAILED_VALIDATION

    def is_promotable(self) -> bool:
        """Return ``True`` if the run can be promoted without a waiver."""

        return self is RunValidationStatus.PASSED

    def requires_governance_review(self) -> bool:
        """Whether governance review is required before promotion."""

        return self is not RunValidationStatus.PASSED


_ValueInput = Union[str, RunValidationStatus]


def coerce_validation_status(value: _ValueInput) -> RunValidationStatus:
    """Convert an arbitrary value to :class:`RunValidationStatus`.

    Parameters
    ----------
    value:
        Either an existing :class:`RunValidationStatus` member or a case-insensitive
        string representation of one of the allowed values.

    Raises
    ------
    ValueError
        If *value* cannot be interpreted as a known validation status.
    """

    if isinstance(value, RunValidationStatus):
        return value

    normalized = value.strip().upper()
    for candidate in RunValidationStatus:
        if candidate.value == normalized:
            return candidate
    raise ValueError(f"Unknown run validation status: {value!r}")


def is_failed_validation(value: _ValueInput) -> bool:
    """Predicate indicating whether a status is a hard failure."""

    return coerce_validation_status(value).is_failed()


def is_promotable(value: _ValueInput) -> bool:
    """Predicate indicating whether a run may be promoted without waiver."""

    return coerce_validation_status(value).is_promotable()


def requires_governance_review(value: _ValueInput) -> bool:
    """Predicate that flags statuses requiring manual governance review."""

    return coerce_validation_status(value).requires_governance_review()


def all_statuses() -> Iterator[RunValidationStatus]:
    """Return an iterator of all possible statuses."""

    return iter(RunValidationStatus)
