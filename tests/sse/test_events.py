import json

from fastapi.testclient import TestClient

from api.app import create_app
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def _run_config():
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"short_window": 3, "long_window": 6})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 3, "long_window": 6}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 1.0}),
        execution=ExecutionSpec(fee_bps=0.0, slippage_bps=0.0),
        validation=ValidationSpec(),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        seed=123,
    )


def _create_run(client: TestClient, cfg: RunConfig):
    resp = client.post("/runs", json=json.loads(cfg.canonical_json()))
    assert resp.status_code == 200
    data = resp.json()
    return data["run_hash"], data["created"]


def parse_sse(raw: str):
    events = []
    for block in [b for b in raw.strip().split("\n\n") if b.strip()]:
        eid = etype = None
        payload = None
        for ln in block.splitlines():
            if ln.startswith("id: "):
                eid = int(ln[4:].strip())
            elif ln.startswith("event: "):
                etype = ln[7:].strip()
            elif ln.startswith("data: "):
                payload = json.loads(ln[6:])
        if eid is not None and payload is not None:
            # Flatten if payload itself wraps type/ts/data
            data_field = payload.get("data", payload)
            events.append({"id": eid, "type": etype, "data": data_field})
    return events


def test_sse_events_and_resume():
    app = create_app()
    client = TestClient(app)
    run_hash, created = _create_run(client, _run_config())
    assert created is True

    # Initial stream
    resp = client.get(f"/runs/{run_hash}/events")
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    # Expect at least heartbeat then snapshot
    types = [e["type"] for e in events]
    assert types[0] == "heartbeat"
    assert "snapshot" in types
    snapshot = next(e for e in events if e["type"] == "snapshot")
    # Some implementations may omit run_hash inside data; if present validate, else ensure summary present
    assert snapshot["data"]["run_hash"] == run_hash
    last_id = events[-1]["id"]

    # Resume with Last-Event-ID should yield no new events (since stream ends baseline)
    resp2 = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": str(last_id)})
    events2 = parse_sse(resp2.text)
    assert events2 == []

    # If we re-request without Last-Event-ID we should get full buffer again
    resp3 = client.get(f"/runs/{run_hash}/events")
    events3 = parse_sse(resp3.text)
    assert len(events3) == len(events)


def test_sse_stream_incremental_and_etag():
    app = create_app()
    client = TestClient(app)
    run_hash, _ = _create_run(client, _run_config())

    # Initial flush fetch with ETag
    r1 = client.get(f"/runs/{run_hash}/events")
    assert r1.status_code == 200
    etag1 = r1.headers.get("ETag")
    assert etag1 is not None
    body1 = r1.text
    # Repeat with If-None-Match should 304 if no new events
    r2 = client.get(f"/runs/{run_hash}/events", headers={"If-None-Match": etag1})
    # Because body is deterministic and no new events, may be 304
    assert r2.status_code in (200, 304)
    if r2.status_code == 200:
        # Body may differ only in timestamp fields; parse and compare event ids & types
        ev1 = parse_sse(body1)
        ev2 = parse_sse(r2.text)
    assert [(e["id"], e["type"]) for e in ev1] == [(e["id"], e["type"]) for e in ev2]

    # Streaming endpoint should at least yield existing events then heartbeat(s)
    rstream = client.get(f"/runs/{run_hash}/events/stream", headers={"Accept": "text/event-stream"})
    assert rstream.status_code == 200
    # Parse first chunk only (testclient collects full content since generator stops quickly for completed run)
    events = parse_sse(rstream.text)
    assert any(e["type"] == "heartbeat" for e in events)
    # No failure events
    assert not any(e["type"] == "error" for e in events)