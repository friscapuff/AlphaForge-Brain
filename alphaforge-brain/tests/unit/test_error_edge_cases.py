from __future__ import annotations

import asyncio
from typing import Any

from api.app import create_app
from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient

router = APIRouter()


@router.get("/boom")
async def boom() -> dict[str, Any]:
    raise RuntimeError("unexpected failure for testing")


@router.get("/slow")
async def slow() -> dict[str, Any]:
    await asyncio.sleep(0.01)
    return {"ok": True}


@router.get("/batch")
async def batch() -> dict[str, Any]:
    # Simulate multiple field errors surfaced as a 400 HTTPException detail
    raise HTTPException(status_code=400, detail="invalid configuration: a,b,c")


def _client():
    app = create_app()
    app.include_router(router)
    # Do not raise server exceptions so we can assert on structured error JSON
    return TestClient(app, raise_server_exceptions=False)


def test_unexpected_error_has_correlation_and_contract():
    c = _client()
    r = c.get("/boom")
    assert r.status_code == 500
    # Header and body correlation id must match
    hid = r.headers.get("x-correlation-id")
    assert hid
    body = r.json()
    assert body["error_code"] == "internal-error"
    assert body["correlation_id"] == hid
    assert "message" in body


def test_slow_path_still_sets_headers():
    c = _client()
    r = c.get("/slow")
    assert r.status_code == 200
    assert r.headers.get("x-correlation-id")
    assert r.headers.get("x-processing-time-ms")


def test_multiple_field_errors_400_contract():
    c = _client()
    r = c.get("/batch")
    assert r.status_code in (400, 422)
    # Even if details omitted, contract keys should exist
    body = r.json()
    assert "error_code" in body
    assert "message" in body
    assert body.get("correlation_id") == r.headers.get("x-correlation-id")
