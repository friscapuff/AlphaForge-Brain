from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient
from services.metrics_hash import equity_curve_hash, metrics_hash


def _payload(seed: int = 123) -> dict[str, object]:  # mirrors other test helpers
    return {
        "symbol": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z",
        "strategy": {"name": "buy_hold", "params": {"window": 5}},
        "risk": {"model": "none", "params": {}},
        "seed": seed,
    }


def test_run_detail_exposes_hashes_and_they_match_recomputed(tmp_path, monkeypatch) -> None:  # type: ignore
    app = create_app()
    client = TestClient(app)
    # Submit run
    r = client.post("/runs", json=_payload())
    assert r.status_code == 200, r.text
    run_hash = r.json()["run_hash"]
    # Fetch detail
    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    metrics_hash_api = body.get("metrics_hash")
    equity_hash_api = body.get("equity_curve_hash")
    # Basic presence
    assert isinstance(metrics_hash_api, str) and len(metrics_hash_api) > 8
    assert isinstance(equity_hash_api, str) and len(equity_hash_api) > 8
    # Recompute metrics hash from summary.metrics
    summary = body.get("summary") or {}
    metrics = summary.get("metrics", {}) if isinstance(summary, dict) else {}
    recomputed_mh = metrics_hash(metrics)
    assert recomputed_mh == metrics_hash_api
    # Load equity parquet and recompute equity_curve_hash
    # artifact listing endpoint provides file names
    art = client.get(f"/runs/{run_hash}/artifacts")
    assert art.status_code == 200
    files = {f["name"] for f in art.json().get("files", [])}
    if "equity.parquet" in files:
        client.get(
            f"/runs/{run_hash}/artifacts/equity.parquet"
        )  # fetch to ensure endpoint works
        # Parquet returns structured response (columns,row_count) so we fall back to direct path read via artifacts root
        # For simplicity, reconstruct path and read locally.
        from infra.artifacts_root import resolve_artifact_root

        path = resolve_artifact_root(None) / run_hash / "equity.parquet"
        if path.exists():
            from lib.artifacts import read_parquet_or_csv

            df = read_parquet_or_csv(path)
            recomputed_eh = equity_curve_hash(df)
            assert recomputed_eh == equity_hash_api
    else:
        # If equity not produced, equity_curve_hash may still be None; allow but document
        assert equity_hash_api is None or isinstance(equity_hash_api, str)
