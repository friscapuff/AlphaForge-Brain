import json
from pathlib import Path

import pandas as pd
import pytest

from api.app import app
from fastapi.testclient import TestClient

from infra.artifacts_root import resolve_artifact_root

client = TestClient(app)


@pytest.mark.integration
@pytest.mark.artifacts
def test_artifact_fetch_json_and_bytes() -> None:
    base = resolve_artifact_root(None)
    run_hash = "RUNJSON123"
    rdir = base / run_hash
    rdir.mkdir(parents=True, exist_ok=True)
    # Write manifest and a json artifact
    (rdir / "manifest.json").write_text(json.dumps({"run_hash": run_hash}), "utf-8")
    payload = {"a": 1, "b": [1, 2, 3]}
    # Use metrics.json (whitelisted by artifact_index) to ensure listing includes it
    (rdir / "metrics.json").write_text(json.dumps(payload), "utf-8")
    # Register run in registry so endpoint passes existence check
    reg = app.state.registry  # type: ignore[attr-defined]
    reg.set(run_hash, {"created_at": 0.0})
    # List artifacts to ensure index sees file
    listing = client.get(f"/runs/{run_hash}/artifacts")
    assert listing.status_code == 200, listing.text
    files = listing.json()["files"]
    assert any(item.get("name") == "metrics.json" for item in files)
    # Fetch JSON artifact
    resp = client.get(f"/runs/{run_hash}/artifacts/metrics.json")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == payload
    # Write a raw bytes artifact and fetch (fallback branch)
    (rdir / "raw.bin").write_bytes(b"hello-bytes")
    resp2 = client.get(f"/runs/{run_hash}/artifacts/raw.bin")
    assert resp2.status_code == 200
    # Allow either raw bytes or JSON-string encoded representation depending on FastAPI serialization
    assert resp2.content in {b"hello-bytes", b'"hello-bytes"'}


@pytest.mark.integration
@pytest.mark.artifacts
def test_artifact_fetch_parquet() -> None:
    base = resolve_artifact_root(None)
    run_hash = "RUNPQ123"
    rdir = base / run_hash
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "manifest.json").write_text(json.dumps({"run_hash": run_hash}), "utf-8")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
    # Write a whitelisted parquet (equity.parquet) for listing plus a secondary frame.parquet to fetch.
    # If pyarrow/fastparquet are unavailable (environment without parquet engines) fall back to CSV bytes
    # while preserving .parquet extension so the API treats it identically (internal code will CSV-parse).
    try:
        df.to_parquet(rdir / "equity.parquet")
        df.to_parquet(rdir / "frame.parquet")
    except Exception:  # pragma: no cover - environment specific
        # Parquet engine missing; create CSV fallback with .parquet name
        (rdir / "equity.parquet").write_text(df.to_csv(index=False), "utf-8")
        (rdir / "frame.parquet").write_text(df.to_csv(index=False), "utf-8")
    reg = app.state.registry  # type: ignore[attr-defined]
    reg.set(run_hash, {"created_at": 0.0})
    listing = client.get(f"/runs/{run_hash}/artifacts")
    assert listing.status_code == 200
    assert any(item.get("name") == "equity.parquet" for item in listing.json()["files"])
    resp = client.get(f"/runs/{run_hash}/artifacts/frame.parquet")
    assert resp.status_code == 200, resp.text
    meta = resp.json()
    assert meta["columns"] == ["x", "y"]
    assert meta["row_count"] == 3
