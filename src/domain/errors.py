from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    retryable = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details, "retryable": self.retryable}


class ValidationError(DomainError):
    code = "INVALID_PARAM"


class NotFoundError(DomainError):
    code = "NOT_FOUND"


class ConflictError(DomainError):
    code = "CONFLICT"


class CancelledError(DomainError):
    code = "CANCELLED"


__all__ = [
    "DomainError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "CancelledError",
]
