from __future__ import annotations

from typing import Any

from domain.errors import DomainError
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
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
    # Map known detail substrings to stable error codes (augmenting legacy HTTPException usage)
    detail_code_map: list[tuple[str, str]] = [
        ("single symbol only", "SINGLE_SYMBOL_ONLY"),
        ("invalid symbol format", "INVALID_SYMBOL"),
        ("run not found", "RUN_NOT_FOUND"),
        ("registry not initialized", "REGISTRY_UNAVAILABLE"),
        ("registry unavailable", "REGISTRY_UNAVAILABLE"),
        ("rate limit exceeded", "RATE_LIMIT"),
        ("limit must be positive", "INVALID_LIMIT"),
        ("artifact not found", "ARTIFACT_NOT_FOUND"),
        ("artifact unreadable", "ARTIFACT_UNREADABLE"),
        ("to must be >= from", "RANGE_INVALID"),
        ("invalid interval", "INTERVAL_INVALID"),
        ("invalid configuration:", "INVALID_CONFIG"),
    ]

    def infer_code(detail: str | None) -> str:
        if not detail:
            return "UNKNOWN_ERROR"
        for marker, code in detail_code_map:
            if detail.startswith(marker):
                return code
        return "UNKNOWN_ERROR"

    @app.exception_handler(DomainError)
    async def domain_error_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:  # pragma: no cover
        status = _CODE_STATUS.get(exc.code, 400)
        return JSONResponse(status_code=status, content=_error_envelope(exc))

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        # Preserve original status while wrapping into structured envelope
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = infer_code(detail)
        body = {
            "detail": detail,
            "error": {
                "code": code,
                "message": detail,
                "retryable": code in {"RATE_LIMIT", "REGISTRY_UNAVAILABLE"},
            },
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=body,
            headers=getattr(exc, "headers", None) or {},
        )

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

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:  # pragma: no cover - simple mapping
        # Collapse FastAPI's default 422 into 400. Surface offending fields (joined) to aid tests & UX.
        try:
            # exc.errors() returns list of dicts with 'loc'
            fields = []
            for err in exc.errors():
                loc = err.get("loc", [])
                if isinstance(loc, (list, tuple)) and len(loc) > 1:
                    fields.append(str(loc[-1]))
            field_list = ",".join(sorted(set(fields))) if fields else "request"
        except Exception:
            field_list = "request"
        # Hybrid behavior: legacy /runs endpoints expect default 422 semantics (tests assert 422),
        # versioned /api/v1/backtests tests expect a consolidated 400 INVALID_PARAM response.
        path = request.url.path if hasattr(request, "url") else ""
        status_code = 422 if path.startswith("/runs") else 400
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": f"invalid configuration: {field_list}",
                "error": {
                    "code": "INVALID_PARAM",
                    "fields": field_list.split(",") if field_list else [],
                    "message": "One or more request fields failed validation",
                    "retryable": False,
                },
            },
        )


__all__ = ["install_error_handlers"]
