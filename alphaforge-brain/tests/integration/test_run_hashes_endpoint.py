from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient

from infra.utils.hash import hash_canonical


def _payload(seed: int = 999) -> dict[str, object]:
    return {
        "symbol": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-01T04:00:00Z",
        "strategy": {"name": "buy_hold", "params": {"window": 3}},
        "risk": {"model": "none", "params": {}},
        "seed": seed,
    }


def test_hashes_endpoint_returns_provenance_hash() -> None:
    app = create_app()
    client = TestClient(app)
    r = client.post("/runs", json=_payload())
    assert r.status_code == 200, r.text
    run_hash = r.json()["run_hash"]
    # call lightweight endpoint
    hresp = client.get(f"/runs/{run_hash}/hashes")
    assert hresp.status_code == 200, hresp.text
    data = hresp.json()
    manifest_hash = data.get("manifest_hash")
    metrics_hash = data.get("metrics_hash")
    equity_curve_hash = data.get("equity_curve_hash")
    provenance_hash = data.get("provenance_hash")
    # Basic presence
    assert isinstance(manifest_hash, str) and len(manifest_hash) > 8
    assert isinstance(metrics_hash, str) and len(metrics_hash) > 8
    # equity hash may be present (equity_curve usually produced); if present assert length
    if equity_curve_hash is not None:
        assert isinstance(equity_curve_hash, str) and len(equity_curve_hash) > 8
    # Reconstruct provenance
    components = {"manifest_hash": manifest_hash, "metrics_hash": metrics_hash}
    if isinstance(equity_curve_hash, str):
        components["equity_curve_hash"] = equity_curve_hash
    expected_prov = hash_canonical(components)
    assert provenance_hash == expected_prov
    # Consistency: run detail endpoint should expose identical values
    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200
    djson = detail.json()
    assert djson.get("metrics_hash") == metrics_hash
    assert djson.get("equity_curve_hash") == equity_curve_hash
