# Tasks: API Error Logging Improvement (009)

**Input**: Design documents from `specs/009-title-api-error/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
- Derived from the tasks template and tailored to the spec decisions.

## Phase 3.1: Setup
- [X] T001 (brain) Confirm backend layout and add error contract module placeholders
  - Paths: `alphaforge-brain/src/api/`, `alphaforge-brain/src/services/`, `alphaforge-brain/src/settings/`
  - Create placeholders: `alphaforge-brain/src/api/errors_contract.py`, `alphaforge-brain/src/settings/error_policy.py`
  - Dependency: none
- [X] T002 (brain) Add Prometheus dependency and /metrics exposure wiring
  - Paths: `alphaforge-brain/src/api/` (app factory or router), `requirements.txt`/`pyproject.toml`
  - Ensure bounded labels and confirm endpoint reachable
  - Dependency: T001
- [X] T003 [P] Configure linting/type checks for new modules
  - Paths: `ruff`/`mypy` configs; ensure new modules included
  - Dependency: none

## Phase 3.2: Tests First (TDD)
- [X] T004 [P] Contract tests: ErrorResponse schema and correlation headers
  - Paths: `alphaforge-brain/tests/contract/test_error_contract.py`
  - Asserts: header `X-Correlation-ID` + body `correlation_id` (must match); `error_code` is kebab-case (e.g., `invalid-param`); `message` present
  - Dependency: T001
- [X] T004a [P] Contract tests: 422 validation field-level details (FR-004)
  - Paths: `alphaforge-brain/tests/contract/test_error_validation_details.py`
  - Asserts: for invalid payloads, HTTP 400/422 returns `details` as a list of objects with `field` and `message` (when present); `error_code` is kebab-case; correlation_id present in header
  - Dependency: T001
- [X] T005 [P] Integration tests: Prod vs Dev/CI verbosity and redaction behavior
  - Paths: `alphaforge-brain/tests/integration/test_error_verbosity_redaction.py`
  - Asserts: Prod = no `debug` block; Dev/CI = `debug` block present on 5xx (no secrets)
  - Dependency: T001
- [X] T005a [P] Integration tests: Server logs stack summary and redacted context (FR-005)
  - Paths: `alphaforge-brain/tests/integration/test_error_logging_stack_summary.py`
  - Asserts: on 5xx, server logs include correlation_id, category, brief stack summary; request context present but redacted; assert via caplog
  - Dependency: T001
- [X] T006 [P] Integration tests: Dependency failure and unexpected error categories
  - Paths: `alphaforge-brain/tests/integration/test_error_categories.py`
  - Asserts: structured body includes top-level `error_code`; categories may include `dependency-unavailable`, `unexpected-internal-error`
  - Dependency: T001
- [X] T007 [P] Metrics tests: /metrics exposes counters/histogram with bounded labels
  - Paths: `alphaforge-brain/tests/integration/test_metrics_errors.py`
  - Asserts: `/metrics` returns text format and exposes `api_error_total{category,endpoint,status}`; labels are bounded
  - Dependency: T002
- [X] T011a [P] Integration tests: Correlation traceability across logs and response (FR-008)
  - Paths: `alphaforge-brain/tests/integration/test_correlation_traceability.py`
  - Asserts: for a failing request, response `X-Correlation-ID` equals the correlation_id emitted in server logs for that request
  - Dependency: T001
- [X] T013a [P] Contract tests: OpenAPI docs for error schema and headers (FR-006)
  - Paths: `alphaforge-brain/tests/contract/test_openapi_error_docs.py`
  - Asserts: `/openapi.json` includes `components.schemas.ErrorResponse` and `components.headers.X-Correlation-ID`; codes use kebab-case
  - Dependency: T001
- [X] T004b [P] Deterministic structure tests (FR-010)
  - Paths: `alphaforge-brain/tests/contract/test_error_determinism.py`
  - Asserts: repeated identical failure modes yield identical error structures (excluding correlation and time); stable top-level keys (`error_code`, `message`, `correlation_id`)
  - Dependency: T001

## Phase 3.3: Core Implementation
- [X] T008 (brain) Correlation middleware
  - Paths: `alphaforge-brain/src/api/middleware/correlation.py`, app wiring in main/router
  - Behavior: generate/propagate X-Correlation-ID; mirror in body
  - Dependency: T004
- [X] T009 (brain) Structured exception handlers (422/401-403/5xx dependency/500 unexpected)
  - Paths: `alphaforge-brain/src/api/error_handlers.py`
  - Behavior: return ErrorResponse; choose kebab-case `error_code`; include `correlation_id`; extract validation `details`; emit error logs
  - Dependency: T004
- [X] T010 (brain) Verbosity & redaction policy module
  - Paths: `alphaforge-brain/src/settings/error_policy.py`
  - Behavior: env-governed Prod vs Dev/CI; include safe `debug` block for 5xx only in Dev/CI
  - Dependency: T005
- [X] T011 (brain) Logging integration with ErrorEvent format
  - Paths: `alphaforge-brain/src/lib/logging.py` or existing logger config
  - Behavior: include correlation_id and stack summary for 5xx (server logs only); compatible with pytest caplog
  - Dependency: T009
- [X] T012 (brain) Prometheus metrics instrumentation
  - Paths: `alphaforge-brain/src/api/metrics.py` and handler integration
  - Behavior: expose /metrics; increment `api_error_total{category,endpoint,status}` on errors; bounded labels
  - Dependency: T007
- [X] T013 (brain) OpenAPI/Swagger docs updates
  - Paths: `alphaforge-brain/src/api/app.py` (custom OpenAPI generator)
  - Behavior: document `components.schemas.ErrorResponse` and `components.headers.X-Correlation-ID`; kebab-case codes
  - Dependency: T009, T013a

## Phase 3.4: Integration
- [X] T014 (brain) Endpoint audit and wiring for high-impact paths (POST /runs)
  - Paths: `alphaforge-brain/src/api/routes/` handlers touched by errors
  - Behavior: ensure handlers use structured errors and propagate correlation_id
  - Dependency: T009, T008
- [X] T015 (brain) Config surface and defaults
  - Paths: `alphaforge-brain/src/settings/error_policy.py`, `.env`/settings
  - Behavior: `ERROR_VERBOSITY`, `ERROR_REDACTION_MODE`, defaults to Prod; misconfig fallback
  - Dependency: T010

## Phase 3.5: Polish
- [X] T016 [P] Edge-case unit tests (timeouts, batch operations, multiple field errors)
  - Paths: `alphaforge-brain/tests/unit/test_error_edge_cases.py`
  - Dependency: T009
- [X] T017 Performance sanity for middleware/handlers
  - Paths: `alphaforge-brain/tests/perf/test_error_overhead.py`
  - Goal: negligible overhead (<1ms added latency typical path)
  - Dependency: T008, T009
- [X] T018 [P] Docs: quickstart.md and contracts examples
  - Paths: `specs/009-title-api-error/quickstart.md`, `specs/009-title-api-error/contracts/`
  - Artifacts: Added example payloads for 400/404/500 under `specs/009-title-api-error/contracts/`
  - Dependency: T013
- [X] T019 [P] CI wiring: ensure tests run and /metrics not flaky in CI
  - Paths: CI config/tests; reuse existing CI if present
  - Dependency: T007, T012
- [X] T020 Refactor and remove duplication
  - Paths: modules touched in T008–T015
  - Summary: Centralized error-code helpers in `alphaforge-brain/src/api/error_codes.py`; refactored `error_handlers.py` to consume them; added unit tests and docs note.
  - Dependency: All core tasks

## Dependencies
- T004–T007, T011a, T013a, T004a, T004b, T005a precede T008–T013 (tests before implementation)
- T008 precedes T014; T009 precedes T011/T013/T014
- T012 requires T007 (metrics tests ready)

## Parallel Execution
- Example parallel batch 1: T004, T005, T006, T007 [P]
- Example parallel batch 2: T008, T010 [P] after batch 1
- Example parallel batch 3: T011, T012, T013 [P] after T009

## Validation Checklist
- [x] All contracts have tests (T004, T005, T006)
- [x] Entities represented in unit/integration tests and logging (ErrorResponse, ErrorEvent, CorrelationContext)
- [x] Tests precede implementation and pass in CI (as of 2025-10-10)
- [x] Metrics labels are bounded; /metrics scrapes in CI
- [x] No stack traces in Prod responses; debug only in Dev/CI
- FR coverage mapping (verified):
  - [x] FR-004 covered by T004a
  - [x] FR-005 covered by T005a
  - [x] FR-006 covered by T013a
  - [x] FR-008 covered by T011a
  - [x] FR-010 covered by T004b

Verification notes (2025-10-10):
- Full test suite green; coverage ~84.5%.
- Error responses include `X-Correlation-ID` header and matching `correlation_id` in body.
- `/metrics` endpoint exposes `api_error_total{category,endpoint,status}` with bounded labels.
- Example error payloads published under `specs/009-title-api-error/contracts/`.

## Notes
- Docs added: `docs/error-contract.md` describing ErrorResponse, verbosity policy, and correlation tracing.
- Env toggles: `ERROR_VERBOSITY`, `ERROR_REDACTION_MODE` documented and wired with safe defaults (Production when unset).
