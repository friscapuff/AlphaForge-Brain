from api.app import create_app
from fastapi.testclient import TestClient


def make_client():
    app = create_app()
    return TestClient(app)


def minimal_run_config(seed: int | None = 123):
    return {
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 1.0, "fee_bps": 0.5},
        "validation": {
            "permutation": {"n": 10},
            "block_bootstrap": {"n": 10},
            "walk_forward": {"splits": 2},
        },
        "symbol": "NVDA",
        # Use canonical supported timeframe (lowercase per parser)
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": seed,
    }


def test_post_and_get_run_contract_deterministic():
    client = make_client()
    payload = minimal_run_config()
    r1 = client.post("/runs", json=payload)
    assert r1.status_code == 200, r1.text
    data1 = r1.json()
    assert {"run_id", "run_hash", "status", "created_at", "created"}.issubset(data1)

    run_hash = data1["run_hash"]
    r_detail1 = client.get(f"/runs/{run_hash}")
    assert r_detail1.status_code == 200
    detail1 = r_detail1.json()
    # contract keys
    for k in ["run_id", "run_hash", "status", "phase", "artifacts", "summary"]:
        assert k in detail1

    # Repeat submission with same config -> same hash, created False
    r2 = client.post("/runs", json=payload)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["run_hash"] == run_hash
    assert data2["created"] is False

    # Deterministic detail again
    r_detail2 = client.get(f"/runs/{run_hash}")
    detail2 = r_detail2.json()
    assert detail1 == detail2


def test_artifacts_listing_and_fetch():
    client = make_client()
    payload = minimal_run_config(seed=456)
    run_hash = client.post("/runs", json=payload).json()["run_hash"]
    lst = client.get(f"/runs/{run_hash}/artifacts")
    assert lst.status_code == 200
    body = lst.json()
    assert body["run_hash"] == run_hash
    assert isinstance(body.get("files"), list)
    # Fetch manifest if present
    if any(f.get("name") == "manifest.json" for f in body.get("files", [])):
        m = client.get(f"/runs/{run_hash}/artifacts/manifest.json")
        assert m.status_code == 200
        manifest_obj = m.json()
        assert isinstance(manifest_obj, dict)


def test_events_endpoint_snapshot_sequence():
    client = make_client()
    run_hash = client.post("/runs", json=minimal_run_config(seed=789)).json()[
        "run_hash"
    ]
    # First call -> heartbeat + snapshot (ids 0 & 1)
    resp = client.get(f"/runs/{run_hash}/events")
    assert resp.status_code == 200
    text = resp.text.strip().splitlines()
    ids = [ln for ln in text if ln.startswith("id:")]
    assert any("id: 0" in line for line in ids)
    assert any("id: 1" in line for line in ids)
    # Resume after snapshot -> expect 304 or empty depending on etag logic
    etag = resp.headers.get("ETag")
    resp2 = client.get(f"/runs/{run_hash}/events", headers={"If-None-Match": etag})
    assert resp2.status_code in (200, 304)


def test_pin_unpin_rehydrate_cycle():
    client = make_client()
    run_hash = client.post("/runs", json=minimal_run_config(seed=321)).json()[
        "run_hash"
    ]
    # Pin
    r_pin = client.post(f"/runs/{run_hash}/pin")
    assert r_pin.status_code == 200
    assert r_pin.json().get("pinned") is True
    # Unpin
    r_unpin = client.post(f"/runs/{run_hash}/unpin")
    assert r_unpin.status_code == 200
    assert r_unpin.json().get("pinned") is False
    # Rehydrate (noop placeholder)
    r_reh = client.post(f"/runs/{run_hash}/rehydrate")
    assert r_reh.status_code == 200
    assert r_reh.json().get("rehydrated") is True
