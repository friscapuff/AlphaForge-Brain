# API Error Contract, Verbosity Policy, and Correlation Tracing

This document describes the canonical error response shape (ErrorResponse), how verbosity is controlled by environment, and how to trace requests using correlation IDs.

## ErrorResponse

All API errors should conform to the following structure:

- error_code: kebab-case stable identifier (e.g., invalid-param, internal-error)
- message: human-readable summary (safe for end-users in production)
- details: optional list of objects with:
  - field: field name (when applicable)
  - message: a short explanation
  - code: optional detail code
- correlation_id: a UUID echoed back in the `X-Correlation-ID` header and attached to logs
- docs_url: optional link to further documentation
- debug: optional diagnostics object (visible only in development/CI)

Example (validation error):

{
  "error_code": "invalid-param",
  "message": "invalid configuration: symbol",
  "details": [
    {"field": "symbol", "message": "invalid value"}
  ],
  "correlation_id": "f1a2b3c4-..."
}

Example (internal error in development):

{
  "error_code": "internal-error",
  "message": "Internal server error",
  "correlation_id": "f1a2b3c4-...",
  "debug": {
    "stack_summary": "Traceback (most recent call last): ..."
  }
}

## Verbosity and Redaction Policy

Verbosity is controlled by the `ERROR_VERBOSITY` environment variable:

- production (default): user-safe messages, no `debug` block
- development: includes a safe `debug` block on server errors (no secrets)
- ci: same as development

Set via environment:

```powershell
$env:ERROR_VERBOSITY = "development"
```

Redaction mode is controlled by `ERROR_REDACTION_MODE`:

- strict (default): aggressively remove potentially sensitive values from responses/logs
- relaxed: allow limited, non-sensitive placeholders (e.g., "[redacted]")

Set via environment:

```powershell
$env:ERROR_REDACTION_MODE = "strict"   # or "relaxed"
```

## Correlation Tracing

- Each request/response is associated with a correlation ID.
- The server will honor an incoming `X-Correlation-ID` header or generate one.
- The correlation ID is returned in the `X-Correlation-ID` response header and included in the ErrorResponse body.
- Server logs include the correlation_id to tie together traces.

## OpenAPI

The OpenAPI schema includes:

- `components.schemas.ErrorResponse`
- `components.headers.X-Correlation-ID`

Use these components to document error responses and headers in your routes.

## Error Codes

Error codes are kebab-case stable identifiers (e.g., `invalid-param`, `dependency-unavailable`, `internal-error`).
They are defined via a centralized registry in `api.error_codes` that standardizes:

- canonical normalization (`to_kebab`)
- mapping of common message prefixes to codes (`infer_code_from_detail`)
- mapping of domain codes to HTTP status (`map_domain_code_to_status`)

Prefer importing from `api.error_codes` when adding new codes or inferring codes from legacy messages to keep docs and implementation in sync.

See also: `docs/error-codes.md` (auto-generated table). To regenerate:

```powershell
python scripts/docs/generate_error_code_reference.py --out docs/error-codes.md
```
