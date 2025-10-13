"""Helpers for mapping validation aggregates to run-level statuses (US1/T013)."""

from __future__ import annotations

from models.run_validation_status import RunValidationStatus

from .aggregator import ValidationAggregate


def determine_validation_status(aggregate: ValidationAggregate) -> RunValidationStatus:
    """Convert a :class:`ValidationAggregate` into a ``RunValidationStatus`` value."""

    significance = (aggregate.validation_significance or "").lower()
    if significance == "fail" or aggregate.failed_checks:
        return RunValidationStatus.FAILED_VALIDATION
    if significance == "caution" or aggregate.caution_checks:
        return RunValidationStatus.CAUTION
    return RunValidationStatus.PASSED


__all__ = ["determine_validation_status"]
