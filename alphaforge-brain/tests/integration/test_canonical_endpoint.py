from __future__ import annotations

import json
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from src.api.app import app
from src.infra.utils.hash import canonical_json, hash_canonical

client = TestClient(app)


def test_canonical_endpoint_basic_round_trip() -> None:
    payload = {"b": 2, "a": 1}
    r = client.post("/canonical/hash", json={"payload": payload})
    assert r.status_code == 200, r.text
    data = r.json()
    # canonical should equal local canonical_json
    assert data["canonical"] == canonical_json(payload)
    assert data["sha256"] == hash_canonical(payload)


def test_canonical_endpoint_order_independent_hash() -> None:
    p1 = {"x": 1, "y": {"b": 2, "a": 1}}
    p2 = {"y": {"a": 1, "b": 2}, "x": 1}
    r1 = client.post("/canonical/hash", json={"payload": p1})
    r2 = client.post("/canonical/hash", json={"payload": p2})
    assert r1.status_code == 200 and r2.status_code == 200
    d1 = r1.json()
    d2 = r2.json()
    assert d1["sha256"] == d2["sha256"], "hash must be independent of key order"
    assert d1["canonical"] == d2["canonical"], "canonical JSON must be identical"


def test_canonical_endpoint_float_precision_stability() -> None:
    p = {"v": 3.14159265358979323846}
    r = client.post("/canonical/hash", json={"payload": p})
    assert r.status_code == 200
    data = r.json()
    # Reparse canonical and ensure numeric round trip consistent with backend canonical_json
    reparsed = json.loads(data["canonical"])
    expected = json.loads(canonical_json(p))
    assert reparsed == expected


def test_canonical_endpoint_datetime_and_date_normalization() -> None:
    now_local = datetime(2025, 9, 27, 12, 34, 56, tzinfo=timezone.utc)
    d = date(2025, 9, 27)
    # JSON cannot carry raw datetime objects; clients serialize first.
    payload = {"ts": now_local.isoformat().replace("+00:00", "Z"), "d": d.isoformat()}
    r = client.post("/canonical/hash", json={"payload": payload})
    assert r.status_code == 200
    data = r.json()
    # Backend canonical_json will isoformat datetimes w/ Z suffix
    assert "Z" in data["canonical"], data["canonical"]
    reparsed = json.loads(data["canonical"])
    # On parse back, should remain string forms matching isoformat expectations
    assert reparsed["ts"].endswith("Z"), reparsed["ts"]
    assert reparsed["d"] == d.isoformat()


class Color(Enum):  # simple enum for hashing
    RED = 1
    BLUE = 2


def test_canonical_endpoint_enums_and_paths() -> None:
    # Client would serialize Enum -> its value and Path -> string prior to JSON transport
    payload = {"enum": Color.RED.value, "path": Path("some/dir/file.txt").as_posix()}
    r = client.post("/canonical/hash", json={"payload": payload})
    assert r.status_code == 200
    data = r.json()
    # Enum should reduce to its value (1) and Path to posix string
    reparsed = json.loads(data["canonical"])
    assert reparsed == {"enum": 1, "path": "some/dir/file.txt"}


def test_canonical_endpoint_nested_list_and_ordering() -> None:
    p1: Any = {"alpha": [{"b": 2, "a": 1}, [{"y": 2, "x": 1}, {"x": 1, "y": 2}]]}
    p2: Any = {"alpha": [{"a": 1, "b": 2}, [{"x": 1, "y": 2}, {"y": 2, "x": 1}]]}
    r1 = client.post("/canonical/hash", json={"payload": p1})
    r2 = client.post("/canonical/hash", json={"payload": p2})
    assert r1.status_code == 200 and r2.status_code == 200
    d1 = r1.json()
    d2 = r2.json()
    # Dicts inside lists should canonicalize independently; array order is preserved so the two should match
    assert d1["sha256"] == d2["sha256"]
    assert d1["canonical"] == d2["canonical"]


def test_canonical_endpoint_float_list_precision_mixture() -> None:
    payload = {
        "vals": [
            1.0000000000000002,
            1.0,
            3.14159265358979323846,
            2.71828182845904523536,
        ]
    }
    r = client.post("/canonical/hash", json={"payload": payload})
    assert r.status_code == 200
    data = r.json()
    # Ensure canonical reparse equals local canonical_json parse
    reparsed = json.loads(data["canonical"])
    expected = json.loads(canonical_json(payload))
    assert reparsed == expected
