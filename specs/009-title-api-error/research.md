# Research: API Error Logging Improvement (009)

Date: 2025-10-05
Branch: 009-title-api-error
Spec: specs/009-title-api-error/spec.md

## Problem Statement
- Current API sometimes returns generic 500 errors without actionable detail; root-cause discovery is slow.
- Logs are not consistently correlated to client-visible failures.
- Error information is not standardized; clients can’t reliably branch on error types.

## Goals
- Provide specific, structured errors to clients with correlation_id.
- Ensure server logs contain redacted, correlated context and stack summary for 5xx.
- Emit metrics for error categories/rates for dashboards/alerts.

## Key Decisions (from Clarifications)
- Correlation ID exposure: header X-Correlation-ID and JSON body for all responses.
- Metrics: Prometheus (/metrics) with counters/histograms; bounded label cardinality.
- Verbosity policy: Prod user-safe summaries; Dev/CI may include a debug block.
- Redaction policy: Environment-driven; strict in Prod; Dev/CI masks sensitive fields, truncated bodies allowed.
- Error code format: kebab-case (e.g., dependency-unavailable).

## Pain Points & Risks
- Risk of leaking sensitive data if verbosity/redaction misconfigured → Default to Production-safe; smoke tests.
- Label cardinality explosion in metrics → Enforce small, bounded label sets (category, endpoint, status only).
- Client coupling to error codes → Use stable kebab-case namespace; document in OpenAPI.
- Log PII exposure → Apply allowlist/masking; never log secrets/tokens; env fallback to strict.

## Comparable Patterns
- Prometheus best practices for HTTP error metrics.
- Correlation ID propagation (traceparent or custom header).
- API error contracts (Stripe-style structured error JSON).

## Acceptance Mapping (Spec ↔ Tests)
- 422 validation → structured field errors, correlation_id header/body.
- 5xx unexpected → structured error with correlation_id and user-safe details (Prod) or debug block (Dev/CI); logs include stack summary.
- Dependency failure → dependency-unavailable code with remediation hint; logs name the dependency.
- Metrics → /metrics exposes api_error_total and optional api_error_latency_seconds.

## Out of Scope (for this feature)
- Full distributed tracing; only correlation_id required.
- Vendor-specific dashboards; we target Prometheus format only.
- Multi-tenant privacy controls beyond redaction rules above.

## Open Questions (post-clarify)
- None critical; proceed to planning and tasks.
