from __future__ import annotations

import logging
import traceback
from collections.abc import Iterable
from typing import Any

from api.error_codes import infer_code_from_detail, map_domain_code_to_status, to_kebab
from api.errors_contract import ErrorDetail, ErrorResponse
from api.metrics import HAS_PROM, api_error_total
from domain.errors import DomainError
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from settings.error_policy import ErrorPolicy


def _corr_id_from_request(request: Request) -> str | None:
    return getattr(
        getattr(request, "state", object()), "correlation_id", None
    ) or request.headers.get("x-correlation-id")


def _safe_fields_from_validation_errors(
    errors: Iterable[dict[str, Any]] | None
) -> list[str]:
    fields: list[str] = []
    if not errors:
        return fields
    for err in errors:
        loc = err.get("loc", []) if isinstance(err, dict) else []
        if isinstance(loc, (list, tuple)) and len(loc) > 1:
            fields.append(str(loc[-1]))
        elif isinstance(err, dict):
            msg = str(err.get("msg", ""))
            for candidate in ("end", "start"):
                if candidate in msg:
                    fields.append(candidate)
    # Deduplicate and stable order
    return sorted(set(fields))


def _maybe_inc_metric(category: str, endpoint: str, status: int) -> None:
    try:
        if HAS_PROM and api_error_total is not None:
            api_error_total.labels(
                category=category, endpoint=endpoint, status=str(status)
            ).inc()
    except Exception:
        # Metrics best-effort only
        pass


def install_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(DomainError)
    async def domain_error_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:  # pragma: no cover - exercised indirectly in higher tests
        # Load policy (may influence future behavior; currently ensures env-parsing side effects)
        ErrorPolicy.load_from_env()
        status = map_domain_code_to_status(getattr(exc, "code", None))
        corr_id = _corr_id_from_request(request)
        # Build new contract while keeping legacy envelope for compatibility
        kebab = to_kebab(getattr(exc, "code", None))
        msg = (
            getattr(exc, "message", None)
            or getattr(exc, "detail", None)
            or "Domain error"
        )
        body: dict[str, Any] = ErrorResponse(
            error_code=kebab,
            message=str(msg),
            correlation_id=str(corr_id) if corr_id else None,
            details=None,
            docs_url=None,
            debug=None,
        ).model_dump(exclude_none=True)
        legacy = getattr(exc, "to_dict", None)
        if callable(legacy):
            try:
                body["error"] = legacy()
            except Exception:
                pass
        _maybe_inc_metric(
            "domain", request.url.path if hasattr(request, "url") else "", status
        )
        headers = {"X-Correlation-ID": str(corr_id)} if corr_id else {}
        return JSONResponse(status_code=status, content=body, headers=headers)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        # Preserve original status while wrapping into structured envelope
        policy = ErrorPolicy.load_from_env()
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = infer_code_from_detail(detail)
        kebab = to_kebab(code)
        corr_id = _corr_id_from_request(request)

        # New contract
        body: dict[str, Any] = ErrorResponse(
            error_code=kebab,
            message=detail,
            correlation_id=str(corr_id) if corr_id else None,
            details=None,
            docs_url=None,
            debug=None,
        ).model_dump(exclude_none=True)
        # Legacy envelope for compatibility
        body["detail"] = detail
        body["error"] = {
            "code": code,
            "message": detail,
            "retryable": code in {"RATE_LIMIT", "REGISTRY_UNAVAILABLE"},
        }

        status_code = int(getattr(exc, "status_code", 400) or 400)
        _maybe_inc_metric(
            "http", request.url.path if hasattr(request, "url") else "", status_code
        )
        # No debug for typical 4xx; if 5xx via HTTPException, optionally include hint in non-prod
        if status_code >= 500 and policy.show_debug:
            body["debug"] = {"stack_summary": ""}

        headers = dict(getattr(exc, "headers", None) or {})
        if corr_id:
            headers.setdefault("X-Correlation-ID", str(corr_id))
        return JSONResponse(status_code=status_code, content=body, headers=headers)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        policy = ErrorPolicy.load_from_env()
        corr_id = _corr_id_from_request(request)
        status = 500
        # Log with correlation for traceability
        try:
            logging.LoggerAdapter(
                logging.getLogger("api.error"), {"correlation_id": corr_id}
            ).error("unhandled_exception", exc_info=exc)
        except Exception:
            pass

        debug_block: dict[str, Any] | None = None
        if policy.show_debug:
            try:
                tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
                # Keep a compact summary to avoid leaking too much
                stack_summary = "".join(tb_lines[-5:]) if tb_lines else ""
                debug_block = {"stack_summary": stack_summary}
            except Exception:
                debug_block = {"stack_summary": ""}

        body: dict[str, Any] = ErrorResponse(
            error_code="internal-error",
            message="Internal server error",
            correlation_id=str(corr_id) if corr_id else None,
            details=None,
            docs_url=None,
            debug=debug_block,  # gated above
        ).model_dump(exclude_none=True)
        # Legacy fields for compatibility
        body["error"] = {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "retryable": False,
        }

        _maybe_inc_metric(
            "unhandled", request.url.path if hasattr(request, "url") else "", status
        )
        headers = {"X-Correlation-ID": str(corr_id)} if corr_id else {}
        return JSONResponse(status_code=status, content=body, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Collapse FastAPI's default 422 into 400 (except legacy /runs). Surface offending fields to aid tests & UX.
        corr_id = _corr_id_from_request(request)
        fields = _safe_fields_from_validation_errors(
            exc.errors() if hasattr(exc, "errors") else None
        )
        field_list = ",".join(fields) if fields else "request"

        path = request.url.path if hasattr(request, "url") else ""
        if path.startswith("/runs") or path.startswith("/backtest"):
            status_code = 422
        else:
            status_code = 400

        # New contract
        details = (
            [ErrorDetail(field=f, message="invalid value") for f in fields]
            if fields
            else None
        )
        body: dict[str, Any] = ErrorResponse(
            error_code="invalid-param",
            message=f"invalid configuration: {field_list}",
            correlation_id=str(corr_id) if corr_id else None,
            details=details,
            docs_url=None,
        ).model_dump(exclude_none=True)
        # Legacy envelope for compatibility
        body["detail"] = f"invalid configuration: {field_list}"
        body["error"] = {
            "code": "INVALID_PARAM",
            "fields": fields,
            "message": "One or more request fields failed validation",
            "retryable": False,
        }

        _maybe_inc_metric("validation", path, status_code)
        headers = {"X-Correlation-ID": str(corr_id)} if corr_id else {}
        return JSONResponse(status_code=status_code, content=body, headers=headers)


__all__ = ["install_error_handlers"]
