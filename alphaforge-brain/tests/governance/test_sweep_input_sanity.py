from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _base_payload() -> dict[str, object]:
    return {
        "start": "2024-01-01",
        "end": "2024-01-05",
        "symbol": "SANITY",
        "timeframe": "1m",
        "strategy": {"name": "dual_sma"},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
    }


def test_missing_range_step_rejected_by_trust_gate() -> None:
    payload = _base_payload()
    payload["strategy"]["parameters"] = {
        "fast": {"mode": "list", "values": [5, 8]},
        "slow": {"mode": "range", "range": {"start": 30, "stop": 61}},
    }

    response = client.post("/runs", json=payload)

    assert response.status_code == 422
    detail = response.json().get("detail")
    assert detail
    if isinstance(detail, list):
        assert any("step" in str(item) for item in detail)
    else:
        assert "step" in str(detail)


def test_missing_parameter_values_rejected() -> None:
    payload = _base_payload()
    payload["strategy"]["parameters"] = {
        "fast": {"mode": "list", "values": []},
    }

    response = client.post("/runs", json=payload)

    assert response.status_code == 422
    detail = response.json().get("detail")
    assert detail
    message = str(detail)
    assert "List mode requires" in message or "Exactly one of value" in message
