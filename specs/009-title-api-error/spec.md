# Feature Specification: API Error Logging Improvement

**Feature Branch**: `009-title-api-error`
**Created**: 2025-10-05
**Status**: Final
**Input**: User description: "API Error logging Improvment\nI want to increase the level of API error logging and detail verbosity. I do not want to get generic error messages, I want very specific errors in order for me to know what I need to address and handle.  . \n\nI was on the page attached and wanted to test the system so I posted a run but got hit with an internal server error without understanding where it came from, after some investigation i was able to pinpoint the error but that process should already by strightforward and direct. Lead me directly to the source of the issue."

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no concrete frameworks unless contract boundary required)
- 👥 Written for business stakeholders, not developers
- 🧩 If feature spans both backend (Brain) and frontend (Mind), clearly separate concerns: backend computation vs frontend presentation.

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave it as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question]
2. **Don't guess** missing contract interactions—ask.
3. **Think like a tester**: Each requirement must map to an observable outcome.
4. **Common underspecified areas**: permissions, data retention, performance targets, error handling, integration boundaries, security/compliance.

---

## Clarifications

### Session 2025-10-05

- Q: Where should correlation_id be exposed to clients on every response (including errors)? → A: Header and body for all responses
- Q: Which metrics system should record error categories/rates? → A: Prometheus (counters/histograms via /metrics)
- Q: What is the verbosity policy for error messages returned to clients? → A: Prod = user-safe summaries; Dev/CI = verbose details
- Q: What’s the redaction scope for sensitive data in logs and error payloads? → A: Environment-driven: strict in Prod, relaxed in Dev/CI
 - Q: What is the error code format for clients to branch on? → A: kebab-case (e.g., dependency-unavailable)

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a developer or operator using the API, I need responses to include specific, actionable error information and a way to correlate the failure with server-side logs so I can quickly determine the root cause and fix it without guesswork.

### Acceptance Scenarios
1. Given a client submits an invalid request to POST /runs, When validation fails, Then the API returns HTTP 422 with field-level error details, standardized error codes, and a correlation_id present in headers and body.
2. Given an unexpected server-side exception occurs during a request, When the API handles the error, Then the client receives HTTP 500 with a structured error body (error_code, message, details) and a correlation_id (in headers and body). In Production, details are user-safe summaries; in Dev/CI, a `debug` block may include diagnostics (e.g., stack summary, hint). Server logs always include a stack summary and redacted request context that can be found using correlation_id.
3. Given a downstream dependency (e.g., database) is unavailable, When a request fails due to dependency issues, Then the API returns a 5xx with error_code "dependency-unavailable", a human-readable error message, and remediation hints, and the logs include the dependency name and error.
4. Given a user lacks permission, When accessing a protected endpoint, Then the API returns 401/403 with a structured error body and does not leak sensitive implementation details, and the logs show the principal and failed permission check with correlation_id.
5. Given a developer wants to investigate a failure, When they search logs using the correlation_id from the response, Then they can trace the request lifecycle including timing and error source category.
6. Given the redaction policy, When running in Production, Then error responses and logs contain no secrets/tokens and no directly identifying PII or full request bodies; When running in Dev/CI, Then secrets/tokens are still redacted and request bodies may be partially included (truncated) with sensitive fields masked to aid debugging.

### Edge Cases
- Large request bodies containing PII: ensure redaction in logs while preserving enough context to debug.
- Multi-error scenarios (e.g., multiple invalid fields): response aggregates errors deterministically.
- Timeouts or cancellations: distinguish client-cancelled vs server timeout in error_code and logs.
- Batch operations: include per-item error details with shared correlation context.
 - Production must never leak stack frames or sensitive internals even under misconfiguration; include a smoke test asserting absence of stack frames in Production responses.
 - Misconfiguration fallback: if environment cannot be determined, default to Production (strict) redaction.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST return structured error responses with fields: error_code, message, details, correlation_id, and documentation link.
- **FR-002**: System MUST include a correlation identifier for every response in both locations: response header (X-Correlation-ID) and JSON body; the same value MUST also appear in server logs for the request lifecycle.
- **FR-003**: System MUST categorize errors into standardized types (VALIDATION, AUTH, PERMISSION, DEPENDENCY, RATE_LIMIT, UNEXPECTED) and use kebab-case error_code values aligned to category naming. Examples: `validation-missing-field`, `auth-unauthorized`, `dependency-unavailable`.
- **FR-004**: System MUST provide field-level validation error details for 4xx validation failures with stable keys.
- **FR-005**: System MUST produce server-side logs that include the correlation_id, error category, brief stack summary for 5xx, and a redacted snapshot of relevant request context.
- **FR-006**: System MUST document the error response contract and codes in API docs, including examples.
   - Implemented: OpenAPI includes `components.schemas.ErrorResponse` and `components.headers.X-Correlation-ID`; example contracts published under `specs/009-title-api-error/contracts/`.
- **FR-007**: System MUST preserve security: no sensitive data in error messages; PII and secrets are redacted in logs.
- **FR-008**: System MUST enable tracing a sample failing request across the request lifecycle using correlation_id.
- **FR-009**: Verbosity policy MUST be environment-governed: Production responses contain user-safe summaries only (no stack traces, internal identifiers, or secrets). In Dev and CI, responses MAY include a `debug` block (e.g., stack_summary, hint) to accelerate diagnosis. A single configuration setting MUST control this behavior and default to Production mode if unset. Under no circumstance may secrets/PII be emitted.
- **FR-010**: System MUST return deterministic error structures for identical failure modes, enabling reliable client handling and tests.
- **FR-011**: System MUST provide actionable remediation hints for common failure categories (e.g., invalid config, missing field, dependency down).
- **FR-012**: System MUST record Prometheus metrics for error categories and rates, exposed at `/metrics` in Prometheus text format. Include at minimum:
   - Counter: `api_error_total{category,endpoint,status}`
   - Optional histogram: `api_error_latency_seconds{category,endpoint}`
   Label cardinality MUST be bounded (no unbounded values like raw error messages or IDs), and metrics MUST be suitable for dashboards/alerts.
   - Implemented: `api_error_total{category,endpoint,status}` exposed; labels restricted to bounded sets.

- **FR-013**: Redaction policy MUST be environment-driven: (a) Production: redact credentials/tokens/secrets and directly identifying PII (e.g., email, phone, names) and do not log full request/response bodies; only minimal safe metadata (method, path, status, timings, correlation_id) may appear. (b) Dev/CI: always redact credentials/tokens/secrets; PII and sensitive fields MUST be masked; request bodies MAY be logged in truncated form (bounded size) for debugging.

### Cross-Project Boundary
- Brain (backend): Enforce structured error response schema, correlation_id generation/propagation, error categorization, logging with redaction, metrics emission.
- Mind (frontend): Display user-safe error messages and correlation_id; provide link to troubleshooting docs; do not attempt to infer categories from raw errors.

### Key Entities
- **ErrorResponse**: error_code (kebab-case), message, details, correlation_id, docs_url.
   - Implemented shape: Always includes `error_code`, `message`, `correlation_id`; `details` present for validation paths; `debug` block gated by environment (Dev/CI only); `docs_url` optional.
- **CorrelationContext**: correlation_id, request metadata (method, path, timestamps), redaction policy; location: response header `X-Correlation-ID` and JSON body.
- **ErrorEvent**: category, error_code, correlation_id, stack summary, request context (redacted), remediation hint.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified
- [x] If dual project: Brain/Mind boundary defined

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (resolved in clarifications)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

Artifacts and verification (2025-10-10):
- Contracts examples: see `specs/009-title-api-error/contracts/` (400/404/500 examples)
- Docs: `docs/error-contract.md` updated with verbosity and redaction policy parameters
- Tests: Contract, integration, and perf tests cover requirements; full suite passing

---
