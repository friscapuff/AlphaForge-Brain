from __future__ import annotations

from pydantic import BaseModel, Field


class DebugBlock(BaseModel):
    """Optional diagnostics visible in Dev/CI only.

    Never include secrets/PII. This is a placeholder shape; details will be
    finalized by tests (T005, T004b) and spec alignment.
    """

    stack_summary: str | None = None
    hint: str | None = None


class ErrorDetail(BaseModel):
    """Field-level validation detail or contextual error note."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Canonical error response contract (FR-001).

    - error_code: kebab-case stable identifier
    - message: human-readable summary (user-safe in Prod)
    - details: optional list of field/context details
    - correlation_id: mirrors X-Correlation-ID response header
    - docs_url: link to troubleshooting/docs
    - debug: optional diagnostics for Dev/CI (never secrets)
    """

    error_code: str = Field(..., description="kebab-case error code")
    message: str
    details: list[ErrorDetail] | None = None
    correlation_id: str | None = None
    docs_url: str | None = None
    debug: DebugBlock | None = None


__all__ = [
    "DebugBlock",
    "ErrorDetail",
    "ErrorResponse",
]
