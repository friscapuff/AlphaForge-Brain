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
_CONTRACT_PATH = _FEATURE_DIR / "contracts" / "manifest.trust_gate.example.json"


@pytest.mark.contract
def test_manifest_includes_trust_gate_extension(tmp_path) -> None:
    """FR-209: Run manifest must embed trust_gate summary block."""

    expected_manifest = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
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
    run_hash = creation.json()["run_hash"]

    manifest_path = Path("artifacts") / run_hash / "manifest.json"
    assert manifest_path.exists(), "Expected manifest.json to be written for run"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trust_gate = manifest["trust_gate"]
    expected = expected_manifest["trust_gate"]

    assert trust_gate["schema_version"] == expected["schema_version"]
    assert trust_gate["suite_version"] == expected["suite_version"]
    assert trust_gate["tolerance_profile"] == expected["tolerance_profile"]
    assert trust_gate["gates"], "Per-gate status list should not be empty"
    assert trust_gate["signature_path"].startswith("artifacts/trust_gates/reports/")
