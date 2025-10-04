# Implementation Plan: Unified Trade & Equity Consistency Initiative

**Branch**: `008-trade-model-proliferation` | **Date**: 2025-10-01 | **Spec**: `specs/008-trade-model-proliferation/spec.md`
**Input**: Feature specification from `/specs/008-trade-model-proliferation/spec.md`

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
Unify execution lifecycle abstractions (Fill, CompletedTrade, EquityBar), consolidate metrics + hashing, remove arbitrary NAV scaling, surface validation caution gating, and lay groundwork for future walk-forward optimization while deferring grid execution. Maintain historical hash stability (trade model version excluded). Provide migration tooling and staged rollout under feature flags.

## Technical Context
**Language/Version**: Python 3.11 (strict typing, mypy + ruff) / Frontend TS 5.x
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Pandas, PyArrow (optional), React, Zustand, lightweight-charts
**Storage**: SQLite (ORM tables: trades, equity, validation, runs), filesystem artifacts (JSON, Parquet/CSV fallback)
**Testing**: pytest (unit/integration/determinism), frontend Vitest/Playwright, hash regression harness
**Target Platform**: Local dev & CI (Linux/Windows parity), future containerized deployment
**Project Type**: dual-project brain+mind
**Performance Goals**: <5% median runtime regression (10k bars), early alert at ≥3%; hashing unchanged except intentional; equity normalization O(n) same complexity
**Constraints**: Determinism, backward compatibility for legacy artifacts, no DB schema loss, feature-flagged rollout
**Scale/Scope**: Single-symbol backtests presently; design must not preclude multi-symbol extension

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

**Structure Decision**: Dual project (AlphaForge Brain + AlphaForge Mind); no cross-root imports; only API + artifact contracts.

## Phase 0: Outline & Research
Objectives:
- Inventory all existing trade/equity representations & their call sites
- Capture baseline determinism hashes (pre-refactor) for 3 canonical strategies
- Benchmark current runtime (10k bars) 5-run median
- Document metric key inventory & collision points
- Assess equity scaling removal impact on downstream metrics

Deliverables (research.md):
- Table: model -> file -> usage count
- Baseline hash manifest JSON
- Performance benchmark table & methodology
- Risk register (precision, migration, adoption, retention gating)
- Decision log referencing Clarifications Session 2

Entry Criteria: Constitution check PASS, Clarifications recorded.
Exit Criteria: All NEEDS CLARIFICATION resolved, baseline artifacts persisted.

## Phase 1: Design & Contracts
Objectives:
- Define canonical Pydantic models: Fill, CompletedTrade, EquityBar (unchanged fields), MetricsSummary (if needed alias only)
- Draft migration mapping (legacy → canonical) with compatibility adapters
- Specify API payload diffs (`validation_caution`, `optimization_mode`, `advanced.warnings`)
- Define hashing consolidation API: `hashes.metrics_signature`, `hashes.equity_signature`
- Introduce deterministic settings module with drawdown epsilon

Deliverables (data-model.md, contracts/*, quickstart.md):
- Data model diagrams & field semantics
- Contract schema diffs (Markdown + JSON examples)
- Quickstart: enabling feature flags, running migration dry-run, comparing hashes

Entry Criteria: Phase 0 complete.
Exit Criteria: No constitution violations; all new contracts version impact assessed (no MAJOR bump needed).

## Phase 2: Task Planning Approach
Approach (tasks.md to be generated in /tasks command):
- Clustered tasks by dependency chain: Models → Adapters → Metrics/Hashing → Equity Normalization → Validation Gating → Optimization Warning → Migration → Cleanup
- Tag tasks with: Root (brain/mind/shared), Risk (L/M/H), Flag Name, Affects Hash (Y/N)
- Include pre/post hash snapshot tasks before and after each cluster
- Include rollback notes (revert to legacy path via feature flag) per cluster

NOT executed here; only approach defined.

## Phase 3+: Future Implementation (Preview)
Phase 3 (Execution): Implement Phases 1 deliverables behind flags; add canonical models & adapters.
Phase 4: Consolidate metrics & hashing, dual-run comparison tests.
Phase 5: Equity normalization + regression guard.
Phase 6: Validation gating propagation & retention exclusion logic.
Phase 7: Optimization structured warning + combo guard.
Phase 8: Migration script + manifest version injection.
Phase 9: Flag removal & cleanup (deprecation sweep, docs update).

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Adapter Layer for Legacy Trade Models | Allows incremental rollout & test diffing | Big-bang rename risks wide regression, loss of traceability |
| Feature Flags (2+) | Safe staged deploy | Single toggle would couple unrelated concerns (hashing vs normalization) |
| Dual Hash Computation During Transition | Validates determinism preservation | Blind replacement could mask subtle drift |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (no violations)
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (Session 2 decisions)
- [x] Complexity deviations documented

---
*Based on Constitution v1.1.0 - See `/memory/constitution.md`*
