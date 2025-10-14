from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.governance import router, storage


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_create_benchmark_trend_alert_persists_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _append(alert, *, artifact_dir=None):  # type: ignore[no-untyped-def]
        captured["alert"] = alert
        return Path("/tmp/dummy.jsonl")

    monkeypatch.setattr(storage, "append_benchmark_alert", _append)

    payload = {
        "alert_id": str(uuid4()),
        "generated_at": datetime(2025, 10, 14, 12, 30, tzinfo=timezone.utc).isoformat(),
        "metric_key": "validation.total.mean_ms",
        "baseline_ms": 120.5,
        "observed_ms": 138.0,
        "delta_pct": 14.5,
        "ticket_url": "https://alerts.example.com/bench/123",
        "status": "open",
    }

    client = _build_client()
    response = client.post("/api/internal/governance/benchmark-alerts", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert "alert" in captured
    alert = captured["alert"]
    assert alert.metric_key == "validation.total.mean_ms"
    assert alert.delta_pct == 14.5


def test_update_waiver_cadence_persists_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _write(snapshot, *, artifact_dir=None):  # type: ignore[no-untyped-def]
        captured["snapshot"] = snapshot
        return Path("/tmp/dummy.json")

    monkeypatch.setattr(storage, "write_waiver_cadence_snapshot", _write)

    payload = {
        "generated_at": datetime(2025, 10, 15, 9, 0, tzinfo=timezone.utc).isoformat(),
        "items": [
            {
                "waiver_id": "W-001",
                "fr_ids": ["FR-221"],
                "opened_at": "2025-09-01",
                "age_days": 44,
                "escalation_status": "normal",
                "next_action": "Follow-up",
            }
        ],
    }

    client = _build_client()
    response = client.post("/api/internal/governance/waiver-cadence", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "persisted"
    assert "snapshot" in captured
    snapshot = captured["snapshot"]
    assert snapshot.generated_at.isoformat().startswith("2025-10-15")
    assert len(snapshot.items) == 1
