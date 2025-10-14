from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import validate_configs


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload, expected_missing",
    [
        ("name: tolerance\n", "threshold"),
        ("threshold: 0.75\n", "name"),
    ],
)
def test_ensure_schema_matches_raises_for_missing_required_fields(
    tmp_path: Path, payload: str, expected_missing: str
) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["name", "threshold"],
                "properties": {
                    "name": {"type": "string"},
                    "threshold": {"type": "number", "minimum": 0},
                },
            }
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(payload, encoding="utf-8")

    with pytest.raises(validate_configs.SchemaValidationError) as excinfo:
        validate_configs.ensure_schema_matches(config_path, schema_path)

    assert expected_missing in str(excinfo.value)


def test_require_signed_change_entry_requires_signature(tmp_path: Path) -> None:
    change_log_path = tmp_path / "CHANGES.md"
    change_log_path.write_text(
        "- 2025-10-14: Updated tolerances at configs/trust_gates/tolerances/causality.yaml\n",
        encoding="utf-8",
    )

    target = Path("configs/trust_gates/tolerances/causality.yaml")

    with pytest.raises(validate_configs.ChangeLogValidationError) as excinfo:
        validate_configs.require_signed_change_entry(target, change_log_path)

    assert "Signed-off-by" in str(excinfo.value)
