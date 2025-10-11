from __future__ import annotations

import importlib

import pytest


@pytest.mark.integration
def test_ci_gating_requires_waiver_for_failed_gate() -> None:
    """FR-210: CI enforcement must block failing gates without waiver."""

    governance = importlib.import_module("services.trust_gates.governance")
    assert hasattr(
        governance, "WaiverRequiredError"
    ), "Governance module must expose WaiverRequiredError"
    assert hasattr(
        governance, "enforce_ci_policy"
    ), "Governance module must expose enforce_ci_policy()"

    summary = {
        "status": "fail",
        "gates": [
            {
                "name": "ingest_idempotency",
                "status": "fail",
                "correlation_id": "tg-test-0003",
                "waiver_ref": None,
            }
        ],
    }

    with pytest.raises(governance.WaiverRequiredError):
        governance.enforce_ci_policy(summary=summary, waivers={})
