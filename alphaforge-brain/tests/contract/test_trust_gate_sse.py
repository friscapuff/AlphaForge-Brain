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
_CONTRACT_PATH = _FEATURE_DIR / "contracts" / "sse-trust_gate-update.example.json"


@pytest.mark.contract
def test_sse_stream_includes_trust_gate_events() -> None:
    """FR-209/FR-210: SSE stream should surface trust gate payloads."""

    expected_event = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))

    creation_payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": "TRUST",
        "timeframe": "1m",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.05}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "seed": 2025,
    }

    creation = _CLIENT.post("/runs", json=creation_payload)
    assert creation.status_code == 200, creation.text
    run_hash = creation.json()["run_hash"]

    response = _CLIENT.get(f"/runs/{run_hash}/events")
    assert response.status_code == 200, response.text
    body = response.text

    assert "trust_gate" in body, "Expected trust gate section to appear in SSE stream"
    assert expected_event["data"]["section"] == "trust_gate"
    assert expected_event["data"]["payload"]["status"] in {"pass", "fail", "warn"}
