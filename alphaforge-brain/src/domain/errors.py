from __future__ import annotations

from typing import Any, ClassVar


class DomainError(Exception):
    code: ClassVar[str] = "DOMAIN_ERROR"
    retryable: ClassVar[bool] = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }


class ValidationError(DomainError):
    code: ClassVar[str] = "INVALID_PARAM"


class NotFoundError(DomainError):
    code: ClassVar[str] = "NOT_FOUND"


class ConflictError(DomainError):
    code: ClassVar[str] = "CONFLICT"


class CancelledError(DomainError):
    code: ClassVar[str] = "CANCELLED"


__all__ = [
    "CancelledError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "ValidationError",
]
