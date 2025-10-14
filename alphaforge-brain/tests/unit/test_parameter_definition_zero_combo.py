from __future__ import annotations

import pytest
from models import parameter_definition as parameter_definition_module
from models.parameter_definition import ParameterDefinition, ParameterDefinitionError
from pydantic import ValidationError


def test_empty_list_payload_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        ParameterDefinition.from_payload(
            name="alpha",
            payload={"mode": "list", "values": []},
        )
    assert "Exactly one of value" in str(exc.value)


def test_zero_combination_error_from_dedup(monkeypatch: pytest.MonkeyPatch) -> None:
    definition = ParameterDefinition.from_payload(name="beta", payload=[1, 1])

    def _empty_dedupe(values):
        return []

    monkeypatch.setattr(
        parameter_definition_module,
        "_dedupe_preserving_order",
        _empty_dedupe,
    )

    with pytest.raises(ParameterDefinitionError, match="zero combinations"):
        definition.normalized_values()
