from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient

from infra.utils.hash import hash_canonical


def _payload(seed: int = 42):
    return {
        "symbol": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-01T02:00:00Z",
        "strategy": {"name": "buy_hold", "params": {"window": 3}},
        "risk": {"model": "none", "params": {}},
        "seed": seed,
    }


def test_provenance_hash_order_independent():
    app = create_app()
    client = TestClient(app)
    r = client.post("/runs", json=_payload())
    assert r.status_code == 200, r.text
    run_hash = r.json()["run_hash"]
    hresp = client.get(f"/runs/{run_hash}/hashes")
    assert hresp.status_code == 200, hresp.text
    data = hresp.json()
    manifest_hash = data.get("manifest_hash")
    metrics_hash = data.get("metrics_hash")
    equity_curve_hash = data.get("equity_curve_hash")
    provenance_hash = data.get("provenance_hash")
    assert isinstance(provenance_hash, str)
    # Rebuild provenance with different insertion order permutations
    components = {"manifest_hash": manifest_hash, "metrics_hash": metrics_hash}
    if isinstance(equity_curve_hash, str):
        components["equity_curve_hash"] = equity_curve_hash
    # Original order hash
    h1 = hash_canonical(components)
    # Reverse order by constructing a list of items reversed
    reversed_items = list(reversed(list(components.items())))
    h2 = hash_canonical(dict(reversed_items))
    assert h1 == h2 == provenance_hash
