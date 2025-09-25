from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

PRESET_PAYLOAD: dict[str, object] = {
    "name": "dual_sma_default",
    "config": {
        "symbol": "TEST",
        "timeframe": "1h",
        "start": 1609459200,
        "end": 1609545600,
        "provider": "local",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"name": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"commission_per_share": 0.0, "slippage_bps": 5},
        "validation": {},
        "seed": 42,
    },
}


def test_presets_idempotent_hash() -> None:
    r1 = client.post("/presets", json=PRESET_PAYLOAD)
    r2 = client.post("/presets", json=PRESET_PAYLOAD)
    assert r1.status_code == 200 or r1.status_code == 201
    assert r2.status_code == 200 or r2.status_code == 201
    b1 = r1.json()
    b2 = r2.json()
    assert b1["preset_id"] == b2["preset_id"], "Preset hashing should be idempotent"
