from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def test_openapi_includes_retention_and_hash_fields():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    # Locate RunDetailResponse schema (model name is path-derived; Pydantic names it 'RunDetailResponse')
    schemas = data.get("components", {}).get("schemas", {})
    run_detail = schemas.get("RunDetailResponse")
    assert run_detail, "RunDetailResponse schema missing"
    props = run_detail.get("properties", {})
    for field in ("pinned", "retention_state", "content_hash"):
        assert field in props, f"{field} missing in OpenAPI RunDetailResponse"


def test_openapi_lists_retention_apply_endpoint():
    app = create_app()
    client = TestClient(app)
    data = client.get("/openapi.json").json()
    paths = data.get("paths", {})
    assert "/runs/retention/apply" in paths, "Retention apply endpoint not documented"
