"""Accounting invariants enforcement utilities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


@dataclass(frozen=True)
class AccountingInvariantViolation:
    """Structured evidence describing an accounting mismatch."""

    delta: Decimal
    tolerance: Decimal
    expected_equity: Decimal
    observed_equity: Decimal
    trade_ids: tuple[str, ...]


@dataclass(frozen=True)
class AccountingInvariantResult:
    """Result of evaluating accounting invariants for a ledger snapshot."""

    passed: bool
    delta: Decimal
    tolerance: Decimal
    expected_equity: Decimal
    observed_equity: Decimal
    violation: AccountingInvariantViolation | None


class AccountingInvariantError(ValueError):
    """Raised when ledger payloads are malformed or missing fields."""


_REQUIRED_FIELDS = ("cash", "unrealized_pnl", "fees", "equity", "tolerance")


def _to_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:  # pragma: no cover - defensive
        raise AccountingInvariantError(
            f"Invalid numeric value for '{field}': {value!r}"
        ) from exc


def _coerce_trade_ids(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return tuple()
    if isinstance(raw, (list, tuple, set)):
        return tuple(str(item) for item in raw)
    return (str(raw),)


def evaluate_ledger(ledger: Mapping[str, Any]) -> AccountingInvariantResult:
    """Evaluate equity invariants for *ledger* and return structured result."""

    if not isinstance(ledger, Mapping):
        raise AccountingInvariantError("ledger payload must be a mapping")

    missing = [field for field in _REQUIRED_FIELDS if field not in ledger]
    if missing:
        raise AccountingInvariantError(
            f"ledger missing required fields: {', '.join(missing)}"
        )

    cash = _to_decimal(ledger.get("cash"), field="cash")
    unrealized = _to_decimal(ledger.get("unrealized_pnl"), field="unrealized_pnl")
    fees = _to_decimal(ledger.get("fees"), field="fees")
    equity = _to_decimal(ledger.get("equity"), field="equity")
    tolerance = abs(_to_decimal(ledger.get("tolerance"), field="tolerance"))

    expected_equity = cash + unrealized + fees
    delta = expected_equity - equity
    passed = abs(delta) <= tolerance

    violation: AccountingInvariantViolation | None
    if passed:
        violation = None
    else:
        violation = AccountingInvariantViolation(
            delta=delta,
            tolerance=tolerance,
            expected_equity=expected_equity,
            observed_equity=equity,
            trade_ids=_coerce_trade_ids(ledger.get("trade_ids")),
        )

    return AccountingInvariantResult(
        passed=passed,
        delta=delta,
        tolerance=tolerance,
        expected_equity=expected_equity,
        observed_equity=equity,
        violation=violation,
    )
