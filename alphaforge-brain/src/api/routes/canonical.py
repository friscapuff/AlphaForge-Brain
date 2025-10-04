"""Canonicalization utility endpoint.

Provides a small helper API to round-trip arbitrary JSON-like payloads through the
backend canonical JSON + hashing layer. This allows the frontend (and external
tools) to verify that a given structure will hash exactly the same way the
backend does when producing provenance / export artifacts.

Response contract kept intentionally tiny so it is stable and easy to snapshot
in tests.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/canonical", tags=["canonical"])

# Use absolute imports (package layout: infra.utils.*). On failure fall back to light module.
try:  # pragma: no cover - import resolution rarely fails
    from infra.utils.hash import canonical_json, hash_canonical
except Exception:  # pragma: no cover
    try:
        from infra.utils.hash_light import (
            canonical_json_light as canonical_json,
        )
        from infra.utils.hash_light import (
            hash_canonical_light as hash_canonical,
        )
    except Exception as e:  # absolute failure -> raise during startup so tests surface
        raise RuntimeError(f"canonical hashing modules unavailable: {e}") from e


class CanonicalizeRequest(BaseModel):
    payload: Any


class CanonicalizeResponse(BaseModel):
    canonical: str
    sha256: str


@router.post("/hash", response_model=CanonicalizeResponse)
async def canonical_hash(
    req: CanonicalizeRequest,
) -> CanonicalizeResponse:  # pragma: no cover - test exercised
    try:
        canon = canonical_json(req.payload)
        digest = hash_canonical(req.payload)
    except Exception as e:  # propagate as 500 for visibility
        raise HTTPException(
            status_code=500, detail=f"canonicalization failed: {e}"
        ) from e
    return CanonicalizeResponse(canonical=canon, sha256=digest)


@router.get("/ping")
async def canonical_ping() -> dict[str, str]:  # pragma: no cover - trivial
    return {"status": "ok"}
