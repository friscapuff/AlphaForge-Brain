# Data Model: API Error Logging Improvement (009)

Date: 2025-10-05
Branch: 009-title-api-error
Spec: specs/009-title-api-error/spec.md

## Entities

### ErrorResponse (JSON)
Fields:
- error_code (string, kebab-case): Stable machine code (e.g., validation-missing-field, dependency-unavailable).
- message (string): Human-readable summary; Prod user-safe; Dev/CI may be more descriptive.
- details (object|null): Optional; structured fields vary by category (see ErrorDetail).
- correlation_id (string, UUID-like): Same value as header X-Correlation-ID.
- docs_url (string, URL): Link to troubleshooting page.
- debug (object|null): Present only in Dev/CI per FR-009; see DebugBlock.

### DebugBlock
Fields (Dev/CI only):
- stack_summary (string[]): Short stack frames summary (top N frames; redacted paths if needed).
- hint (string|null): Short actionable hint.
- sampled (boolean): Indicates if debug was sampled or always on.

### ErrorDetail (category-dependent)
- validation: { field (string), issue (string), expected (string|number|boolean|null) }
- auth/permission: { principal (string|null), required (string) }
- dependency: { name (string), timeout (boolean), upstream_status (number|null) }
- rate-limit: { retry_after_seconds (number) }
- unexpected: { operation (string|null) }

### ErrorEvent (for logs)
Fields:
- timestamp (RFC3339)
- correlation_id (string)
- category (enum: validation|auth|permission|dependency|rate-limit|unexpected)
- error_code (string, kebab-case)
- endpoint (string)
- status (number)
- stack_summary (string[]|null)
- request_context (object): Redacted context (see Redaction Policy)
- remediation_hint (string|null)

### CorrelationContext
Fields:
- correlation_id (string)
- request: { method, path, query (redacted), headers (safe subset), ts_start, ts_end }
- response: { status, ts }
- env: { name: prod|dev|ci }

## Headers
- X-Correlation-ID: Always present; mirrors body.correlation_id; server may honor client-provided value when safe or generate a new one.

## Environment Settings
- ERROR_VERBOSITY: prod|dev|ci (default: prod).
- ERROR_DEBUG_SAMPLING: float 0..1 (dev/ci only; default 1.0).
- ERROR_REDACTION_MODE: prod|dev (default derives from ERROR_VERBOSITY; fallback prod).

## Metrics (Prometheus)
- Counter: api_error_total{category,endpoint,status}
- Optional Histogram: api_error_latency_seconds{category,endpoint}
Notes:
- Do not include correlation_id or raw error messages as labels.
- endpoint should be a templated route (e.g., /runs/{run_hash}).

## OpenAPI / Swagger Notes
- Document ErrorResponse schema with examples for Prod vs Dev/CI.
- Document header X-Correlation-ID for all responses.
- Enumerate known error_code values in descriptions with kebab-case style.

## Examples

### Production 500
{
  "error_code": "dependency-unavailable",
  "message": "Database temporarily unavailable",
  "details": { "name": "sqlite" },
  "correlation_id": "8f8a9af1-2db1-4a8c-9d33-9a3f4e0bf111",
  "docs_url": "https://docs.local/errors/dependency-unavailable"
}

### Dev/CI 500 with debug
{
  "error_code": "unexpected-internal-error",
  "message": "An unexpected error occurred",
  "details": { "operation": "create-run" },
  "correlation_id": "e2b2b9ab-4ef6-4e15-9e55-2f2e6b6b8a22",
  "docs_url": "https://docs.local/errors/unexpected-internal-error",
  "debug": {
    "stack_summary": ["service.py:42 in create_run", "db.py:88 in insert"],
    "hint": "Check DB connection string",
    "sampled": true
  }
}

### 422 Validation
{
  "error_code": "validation-missing-field",
  "message": "Field 'strategy_id' is required",
  "details": { "field": "strategy_id", "issue": "missing", "expected": "uuid" },
  "correlation_id": "22c8a4d9-7d09-4c22-8ae6-6d8b7f3b1c00",
  "docs_url": "https://docs.local/errors/validation-missing-field"
}
