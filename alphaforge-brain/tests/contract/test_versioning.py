from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_versioning_invariants() -> None:  # T010
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    # Version should follow semver-ish pattern or end with +dev
    v = body["version"]
    assert isinstance(v, str)
    assert len(v) > 0
    # basic shape check (digits and dots)
    assert any(ch.isdigit() for ch in v)
