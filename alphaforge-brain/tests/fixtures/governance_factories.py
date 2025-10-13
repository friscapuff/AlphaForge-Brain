"""Factories for governance-related test artifacts.

This module centralises builders used by trust-gate, validation, accounting,
and retention test suites so they can share deterministic fixtures without
hand-crafting dictionaries inside each test module.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping

__all__ = [
    "build_tolerance_metric",
    "build_tolerance_profile",
    "build_validation_gate_result",
    "build_accounting_ledger",
    "build_retention_record",
    "build_retention_policy",
]

_UTC_EPOCH = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _deep_update(dest: MutableMapping[str, Any], updates: Mapping[str, Any]) -> None:
    """Recursively update *dest* with *updates* while preserving nested structures."""

    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(dest.get(key), MutableMapping):
            _deep_update(dest[key], value)  # type: ignore[index]
        else:
            dest[key] = value  # type: ignore[index]


def _apply_overrides(
    base: Mapping[str, Any], overrides: Mapping[str, Any] | None
) -> dict[str, Any]:
    result: dict[str, Any] = copy.deepcopy(base)
    if overrides:
        _deep_update(result, overrides)
    return result


def build_tolerance_metric(**overrides: Any) -> dict[str, Any]:
    """Return a single tolerance metric specification.

    Examples
    --------
    >>> metric = build_tolerance_metric(name="sharpe_ratio")
    >>> metric["threshold"]
    1.5
    """

    base = {
        "name": "sharpe_ratio",
        "comparison": "<=",
        "threshold": 1.5,
        "direction": "below",
        "window": "90d",
        "weight": 1.0,
    }
    return _apply_overrides(base, overrides)


def build_tolerance_profile(**overrides: Any) -> dict[str, Any]:
    """Return a canonical tolerance profile payload with optional overrides."""

    base = {
        "profile_id": "causality-default",
        "schema_version": "1.0.0",
        "metrics": [
            build_tolerance_metric(),
            build_tolerance_metric(
                name="equity_drift",
                comparison="<",
                threshold=0.03,
                direction="below",
                window="30d",
            ),
        ],
        "enforcement_mode": "hard",
        "updated_at": _UTC_EPOCH.isoformat(),
        "metadata": {
            "owner": "governance",
            "description": "Default causality tolerances for institutional runs",
        },
    }
    return _apply_overrides(base, overrides)


def build_validation_gate_result(**overrides: Any) -> dict[str, Any]:
    """Return Masters validation aggregate output suitable for gating tests."""

    base = {
        "run_hash": "RUN_HASH_0001",
        "permutation_p_value": 0.012,
        "cpcv_p_value": 0.018,
        "icc_width": 0.007,
        "status": "PASSED",
        "evidence_artifact": "zz_artifacts/validation/RUN_HASH_0001.json",
        "evaluated_at": _UTC_EPOCH.isoformat(),
        "sample_size": 1024,
        "notes": "Deterministic baseline aggregate",
    }
    return _apply_overrides(base, overrides)


def build_accounting_ledger(**overrides: Any) -> dict[str, Any]:
    """Return a baseline accounting ledger satisfying equity invariants."""

    base = {
        "run_hash": "RUN_HASH_0001",
        "cash": 1_000_000.00,
        "unrealized_pnl": 25_000.25,
        "fees": -2_500.75,
        "equity": 1_022_499.50,
        "tolerance": 1.0,
        "currency": "USD",
        "trade_ids": ["T-100", "T-101", "T-102"],
        "generated_at": _UTC_EPOCH.isoformat(),
    }
    return _apply_overrides(base, overrides)


def build_retention_record(**overrides: Any) -> dict[str, Any]:
    """Return a retention record representing stored run metadata."""

    base = {
        "run_hash": "RUN_HASH_0001",
        "strategy_id": "STRAT_ALPHA",
        "score": 1.34,
        "status": "PASSED",
        "pinned": False,
        "created_at": _UTC_EPOCH.isoformat(),
        "updated_at": _UTC_EPOCH.isoformat(),
        "tags": ["governance", "baseline"],
        "metadata": {
            "schema_version": "1.0.0",
            "validation_status": "PASSED",
        },
    }
    return _apply_overrides(base, overrides)


def build_retention_policy(**overrides: Any) -> dict[str, Any]:
    """Return a baseline retention policy structure for automation tests."""

    base = {
        "policy_version": "2025.10.12",
        "max_runs": 50,
        "per_strategy_top": 5,
        "pin_expiry_days": None,
        "waiver_required": True,
        "audit_log_path": "zz_artifacts/retention_audit.log",
        "annotations": {
            "owner": "governance",
            "description": "Default automation policy for AlphaForge runs",
        },
    }
    return _apply_overrides(base, overrides)
