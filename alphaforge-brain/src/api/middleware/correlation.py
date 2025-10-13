from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response


async def correlation_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.time()
    corr_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = corr_id
    # Delegate exception rendering to FastAPI's handlers to preserve the structured contract
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    response.headers.setdefault("x-correlation-id", corr_id)
    response.headers["x-processing-time-ms"] = str(duration_ms)
    return response


__all__ = ["correlation_middleware"]
