# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

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
[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context
**Language/Version**: [e.g., Python 3.11 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI, React, PyArrow or NEEDS CLARIFICATION]
**Storage**: [e.g., SQLite, Parquet, Local FS or N/A]
**Testing**: [frameworks]
**Target Platform**: [runtime targets]
**Project Type**: [single | web | mobile | brain+mind dual]
**Performance Goals**: [explicit metrics]
**Constraints**: [latency, memory, determinism, security]
**Scale/Scope**: [volume, user count, data size]

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

**Structure Decision**: [choose one; dual project requires contract note]

## Phase 0: Outline & Research
[Same as earlier version; add research for architecture boundary if dual project]

## Phase 1: Design & Contracts
- Identify cross-project contracts: artifact schemas, API endpoints, CLI protocols.
- Document version impact for any new exposed interface.

## Phase 2: Task Planning Approach
[Unchanged core, but tasks MUST tag which project root they modify]

## Phase 3+: Future Implementation
[Same]

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|

## Progress Tracking
**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [ ] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.1.0 - See `/memory/constitution.md`*
