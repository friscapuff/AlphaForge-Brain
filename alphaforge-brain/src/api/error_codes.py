"""Centralized error-code registry and helpers.

Provides:
- to_kebab: normalize error codes to kebab-case
- infer_code_from_detail: map message prefixes to stable codes
- map_domain_code_to_status: translate domain codes to HTTP status

This acts as a single source of truth for error codes across handlers,
docs, and tests.
"""

from __future__ import annotations

from typing import Final

# Domain/HTTP mapping for common codes
DOMAIN_CODE_STATUS: Final[dict[str, int]] = {
    "INVALID_PARAM": 400,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "CANCELLED": 400,  # client-driven state change
}


DETAIL_CODE_MAP: Final[list[tuple[str, str]]] = [
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


def to_kebab(code: str | None) -> str:
    if not code:
        return "unknown-error"
    return code.strip().replace(" ", "-").replace("_", "-").lower()


def infer_code_from_detail(detail: str | None) -> str:
    if not detail:
        return "UNKNOWN_ERROR"
    for marker, code in DETAIL_CODE_MAP:
        if detail.startswith(marker):
            return code
    return "UNKNOWN_ERROR"


def map_domain_code_to_status(code: str | None) -> int:
    return DOMAIN_CODE_STATUS.get(code or "", 400)


# Optional descriptions for docs and examples
CODE_DESCRIPTIONS: Final[dict[str, str]] = {
    "INVALID_PARAM": "One or more request fields failed validation.",
    "NOT_FOUND": "Requested resource was not found.",
    "CONFLICT": "Request conflicts with existing state.",
    "CANCELLED": "Operation was cancelled by the client.",
    "SINGLE_SYMBOL_ONLY": "This endpoint accepts a single symbol only.",
    "INVALID_SYMBOL": "Symbol format is invalid.",
    "RUN_NOT_FOUND": "Run was not found.",
    "REGISTRY_UNAVAILABLE": "Required registry is unavailable.",
    "RATE_LIMIT": "Rate limit exceeded.",
    "INVALID_LIMIT": "Limit must be positive.",
    "ARTIFACT_NOT_FOUND": "Artifact was not found.",
    "ARTIFACT_UNREADABLE": "Artifact cannot be read.",
    "RANGE_INVALID": "Range is invalid (to must be >= from).",
    "INTERVAL_INVALID": "Interval is invalid.",
    "INVALID_CONFIG": "Invalid configuration.",
    "UNKNOWN_ERROR": "Unknown error.",
    "INTERNAL_ERROR": "Internal server error.",
}


def _collect_all_codes() -> list[str]:
    codes: set[str] = set(DOMAIN_CODE_STATUS.keys())
    codes.update(code for _, code in DETAIL_CODE_MAP)
    # Ensure common codes included
    codes.update({"UNKNOWN_ERROR", "INTERNAL_ERROR"})
    return sorted(codes, key=lambda c: to_kebab(c))


def all_codes() -> list[dict[str, str | int]]:
    """Return a list of code metadata dicts for docs and examples.

    Each dict includes: code (CONST), kebab, status (if available), description (if available).
    """
    rows: list[dict[str, str | int]] = []
    for code in _collect_all_codes():
        kebab = to_kebab(code)
        status = DOMAIN_CODE_STATUS.get(code)
        desc = CODE_DESCRIPTIONS.get(code, kebab.replace("-", " ").capitalize() + ".")
        row: dict[str, str | int] = {"code": code, "kebab": kebab, "description": desc}
        if status is not None:
            row["status"] = status
        rows.append(row)
    return rows


def render_markdown_table() -> str:
    """Render a simple Markdown table of all error codes for docs."""
    rows = all_codes()
    lines = ["| Code | Kebab | Status | Description |", "|---|---|---|---|"]
    for r in rows:
        status = str(r.get("status", ""))
        lines.append(f"| {r['code']} | {r['kebab']} | {status} | {r['description']} |")
    return "\n".join(lines) + "\n"


def openapi_example_errors(limit: int = 5) -> list[dict[str, str]]:
    """Return a small set of example ErrorResponse bodies for OpenAPI examples."""
    out: list[dict[str, str]] = []
    for r in all_codes()[: max(1, limit)]:
        out.append({"error_code": str(r["kebab"]), "message": str(r["description"])})
    return out


__all__ = [
    "DETAIL_CODE_MAP",
    "DOMAIN_CODE_STATUS",
    "all_codes",
    "infer_code_from_detail",
    "map_domain_code_to_status",
    "openapi_example_errors",
    "render_markdown_table",
    "to_kebab",
]
