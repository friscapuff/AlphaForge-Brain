from __future__ import annotations

from typing import Any

from domain.errors import DomainError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_CODE_STATUS = {
    "INVALID_PARAM": 400,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "CANCELLED": 400,  # Cancellation as client-driven state change
}


def _error_envelope(err: DomainError) -> dict[str, Any]:
    return {"error": err.to_dict()}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:  # pragma: no cover
        status = _CODE_STATUS.get(exc.code, 400)
        return JSONResponse(status_code=status, content=_error_envelope(exc))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:  # pragma: no cover
        # In dev you might log traceback; response stays generic
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "retryable": False,
                }
            },
        )


__all__ = ["install_error_handlers"]
