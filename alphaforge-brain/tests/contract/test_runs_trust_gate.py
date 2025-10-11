from __future__ import annotations

import json
from pathlib import Path

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

_CLIENT = TestClient(create_app())
_FEATURE_DIR = (
    Path(__file__).resolve().parents[3] / "specs" / "011-trust-gate-framework"
)
_CONTRACT_PATH = _FEATURE_DIR / "contracts" / "api-run.trust_gate.example.json"


@pytest.mark.contract
def test_runs_detail_includes_trust_gate_contract_block() -> None:
    """FR-209/FR-210: API payload must surface trust gate summary information."""

    expected_payload = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))

    creation_payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": "TRUST",
        "timeframe": "1m",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.05}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "seed": 1337,
    }

    creation = _CLIENT.post("/runs", json=creation_payload)
    assert creation.status_code == 200, creation.text
    run_id = creation.json()["run_hash"]

    detail = _CLIENT.get(f"/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()

    trust_gate = body["trust_gate"]
    expected = expected_payload["trust_gate"]

    assert trust_gate["schema_version"] == expected["schema_version"]
    assert trust_gate["tolerance_profile"] == expected["tolerance_profile"]
    assert trust_gate["status"] in {"pass", "fail", "warn"}
    assert trust_gate["gates"], "Expected per-gate summaries in trust_gate.gates"

    for gate in trust_gate["gates"]:
        assert {"name", "status", "artifact", "correlation_id"}.issubset(gate)

    assert trust_gate["signature_path"].startswith("artifacts/trust_gates/reports/")
