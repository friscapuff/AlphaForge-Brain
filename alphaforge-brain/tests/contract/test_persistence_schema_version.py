"""Contract tests for persistence schema enforcement (US2/T017)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from infra.persistence import (
    PersistenceSchemaError,
    validate_persistence_record,
)


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("repository root not found")


def _base_record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_id": "a" * 64,
        "schema_version": "1.0.0",
        "payload": {"name": "governance_artifact", "version": 1},
        "created_at": "2025-10-12T00:00:00Z",
        "source_component": "trust_gate",
        "validation_status": "accepted",
        "migration_history": [],
    }
    for key, value in overrides.items():
        record[key] = value
    return record


def test_validate_persistence_record_accepts_valid_payload(tmp_path: Path) -> None:
    record = _base_record()

    validated = validate_persistence_record(record)

    assert validated["schema_version"] == "1.0.0"
    assert validated["record_id"] == record["record_id"]


def test_validate_persistence_record_requires_schema_version() -> None:
    record = _base_record()
    record.pop("schema_version")

    with pytest.raises(PersistenceSchemaError, match="schema_version"):
        validate_persistence_record(record)


def test_validate_persistence_record_rejects_invalid_record_id() -> None:
    record = _base_record(record_id="invalid")

    with pytest.raises(PersistenceSchemaError, match="record_id"):
        validate_persistence_record(record)


def test_validate_persistence_record_disallows_additional_properties() -> None:
    record = _base_record(extra_field="unexpected")

    with pytest.raises(PersistenceSchemaError, match="additional properties"):
        validate_persistence_record(record)


def test_validate_persistence_record_maintains_immutable_copy() -> None:
    record = _base_record()
    validated = validate_persistence_record(record)

    assert validated is not record
    # ensure original input mutated? verifying copy to avoid call site side effects
    assert record["schema_version"] == "1.0.0"
    assert json.dumps(validated, sort_keys=True)
