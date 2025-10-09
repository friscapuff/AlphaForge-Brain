# Implementation Plan: API Error Logging Improvement (009)

**Branch**: `009-title-api-error` | **Date**: 2025-10-05 | **Spec**: `specs/009-title-api-error/spec.md`
**Input**: Feature specification from `specs/009-title-api-error/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (single, web(frontend+backend), mobile, or dual-project brain+mind)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document (v1.1.0 or later).
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Improve API error specificity, traceability, and diagnosability by:
- Returning structured errors with kebab-case error_code, message, details, docs_url and correlation_id (in header + body).
- Generating/propagating correlation_id across logs and responses.
- Emitting Prometheus metrics for error categories/rates at /metrics.
- Enforcing environment-governed verbosity and redaction (Prod user-safe; Dev/CI can include debug block; secrets never leaked).

## Technical Context
**Language/Version**: Python 3.11 (FastAPI backend)
**Primary Dependencies**: FastAPI, Pydantic, Prometheus client, Logging framework
**Storage**: SQLite (existing), local file artifacts
**Testing**: pytest (unit/contract), possibly httpx client for API tests
**Target Platform**: Local dev, CI
**Project Type**: Dual project (alphaforge-brain backend; mind unaffected functionally)
**Performance Goals**: Negligible overhead; /metrics scrape ok; no >1ms added latency for happy-path requests (goal)
**Constraints**: No secrets in errors; bounded label cardinality; deterministic error shapes
**Scale/Scope**: Single-user dev instance; extendable

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Determinism: Seeds & replay plan documented?
- Test-First: Failing test scaffolds enumerated?
- Modular MVC / Dual Root: Does feature keep Brain (backend analytics) and Mind (frontend UX) isolated?
- Observability: Timing/tracing instrumentation points identified?
- Contract Versioning: Any breaking interface needs MAJOR bump justification?
- Performance Targets: Benchmarks listed with thresholds?
- Data Integrity: Migrations or schema diffs required?

If any FAIL → STOP.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT legacy)
src/
  models/
  services/
  cli/
  lib/

tests/
  contract/
  integration/
  unit/

# Option 2: Web application (frontend + backend)
backend/
  src/
    models/
    services/
    api/
  tests/
frontend/
  src/
    components/
    pages/
    services/
  tests/

# Option 3: Mobile + API
api/
  src/
  tests/
ios/ or android/
  src/
  tests/

# Option 4: Dual Project (AlphaForge Brain + AlphaForge Mind)
alphaforge-brain/
  src/
  tests/
alphaforge-mind/
  src/
  tests/
shared/ (optional strictly pure utilities)
```

**Structure Decision**: Dual project (AlphaForge Brain + AlphaForge Mind); error contract in Brain; Mind renders messages and correlation_id only.

## Phase 0: Outline & Research
- Inventory current error handling path in backend: exception handlers, middleware, logging config.
- Identify endpoints with generic 500s (e.g., POST /runs) and capture sample payloads.
- Review current logging format; confirm presence/absence of request IDs.
- Validate Prometheus client availability; confirm /metrics endpoint exposure path.
- Output: research.md (done), list of touchpoints, risks, and acceptance mapping.

## Phase 1: Design & Contracts
- Define ErrorResponse JSON schema (Prod vs Dev/CI shapes) and header contract.
- Specify correlation_id propagation rules (accept vs override client-provided IDs).
- Define error categories and kebab-case error_code namespace.
- Document Prometheus metrics (names/labels) and /metrics route exposure.
- Contracts folder: JSON examples for 422, 401/403, 5xx dependency, 5xx unexpected.
- Update quickstart.md with env toggles (ERROR_VERBOSITY, ERROR_REDACTION_MODE).

## Phase 2: Task Planning Approach
- Tag tasks by backend module: middleware, exception handlers, logging, metrics, docs/testing.
- Include test scaffolds first (contract + environment policies) to drive implementation.
- Keep Mind tasks minimal (doc link and UI display only if needed later).

## Phase 3+: Future Implementation
- Implement correlation middleware (generate/propagate X-Correlation-ID).
- Implement structured exception handlers: validation (422), auth/perm (401/403), dependency (5xx), unexpected (500).
- Add environment-governed verbosity (debug block only in Dev/CI) and redaction policy; safeguard defaults to Prod.
- Add Prometheus metrics instrumentation with bounded labels; expose /metrics.
- Update OpenAPI examples and docs.
- Tests: contract tests for each error category, header presence, Prod vs Dev/CI behavior, metrics exposure, no stack traces in Prod.

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Env-driven verbosity | Safer production defaults with dev ergonomics | One-size-fits-all would leak or hinder debugging |
| Bounded labels | Prevents Prometheus cardinality explosion | Free-form labels risk memory/CPU blowup |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/tasks command - described approach)
- [x] Phase 3: Tasks generated (/tasks command)
- [x] Phase 4: Implementation complete
- [x] Phase 5: Validation passed (tests green as of 2025-10-10)

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

### Deviations & Notes
- Optional import-order exceptions were handled by refactoring try-import patterns (e.g., Prometheus import) rather than suppressing rules.
- T020 (refactor/duplication removal) deferred to a follow-up housekeeping task.

### Follow-ups (Out-of-Scope)
- Consider consolidating error code registry into a single source-of-truth to aid documentation and validation.
- Expand metrics with a bounded histogram if/when SLOs are defined.

---
*Based on Constitution v1.1.0 - See `/memory/constitution.md`*
