from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _base_payload() -> dict[str, Any]:
    return {
        "start": "2024-01-01",
        "end": "2024-01-07",
        "symbol": "DET",
        "timeframe": "1m",
        "strategy": {"name": "dual_sma"},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
    }


def _cleanup_artifacts(run_hash: str | None) -> None:
    if not run_hash:
        return
    manifest_dir = Path("artifacts") / run_hash
    if manifest_dir.exists():
        shutil.rmtree(manifest_dir, ignore_errors=True)


def _reset_registry() -> None:
    registry = getattr(app.state, "registry", None)
    if registry is not None:
        registry.store.clear()
        registry.progress_counts.clear()


def test_sweep_submission_returns_sweep_metadata() -> None:
    _reset_registry()
    payload = _base_payload()
    payload["strategy"]["parameters"] = {
        "fast": {"mode": "list", "values": [5, 8]},
        "slow": {"mode": "range", "range": {"start": 30, "stop": 61, "step": 15}},
    }

    response = client.post("/runs", json=payload)
    assert response.status_code == 202
    body = response.json()

    assert body["optimization_mode"] == "sweep"
    assert body["combination_count"] == 6
    assert body["sweep_id"]
    assert body["run_hash"] == body["sweep_id"]
    assert body["created"] is True
    assert not (Path("artifacts") / body["run_hash"]).exists()

    # Repeat submission produces identical sweep identifier
    response_repeat = client.post("/runs", json=payload)
    assert response_repeat.status_code == 202
    assert response_repeat.json()["sweep_id"] == body["sweep_id"]


def test_sweep_submission_single_combination_executes_single_run() -> None:
    _reset_registry()
    payload = _base_payload()
    payload["strategy"]["parameters"] = {
        "fast": {"mode": "single", "value": 5},
        "slow": {"mode": "single", "value": 30},
    }

    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert "sweep_id" not in body
    assert body["created"] is True
    run_hash = body["run_hash"]
    assert run_hash
    manifest_path = Path("artifacts") / run_hash / "manifest.json"
    assert manifest_path.exists(), "Expected manifest for single run execution"

    _cleanup_artifacts(run_hash)
