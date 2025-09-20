from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def _payload(seed: int):
    return {
        "start": "2024-03-01",
        "end": "2024-03-02",
        "symbol": "RET",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 10}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "validation": {},
        "seed": seed,
    }


def test_retention_capped_at_100_runs():
    hashes = []
    for i in range(105):
        r = client.post("/runs", json=_payload(seed=i))
        assert r.status_code == 200
        hashes.append(r.json()["run_hash"])

    # Listing should show at most 100 items (recent ones)
    listing = client.get("/runs?limit=100")
    assert listing.status_code == 200
    items = listing.json().get("items", [])
    assert len(items) <= 100

    # Expect exactly the most recent 100 hashes (or fewer if fewer created)
    returned = [it["run_hash"] for it in items]
    # The first returned should be the very last created run hash
    assert returned[0] == hashes[-1]
    # Set equality for content (order not strictly enforced beyond first element check)
    assert set(returned) == set(hashes[-100:])
    # Oldest (first created) hash should not be present after pruning
    assert hashes[0] not in returned
