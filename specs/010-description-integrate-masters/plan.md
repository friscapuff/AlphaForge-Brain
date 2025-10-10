# Implementation Plan: Advanced Statistical Validation Integration

**Branch**: `010-description-integrate-masters` | **Date**: 2025-10-11 | **Spec**: [`specs/010-description-integrate-masters/spec.md`](./spec.md)
**Input**: Feature specification from `/specs/010-description-integrate-masters/spec.md`

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
Integrate Masters-style permutation testing, bias-adjusted Sharpe diagnostics, cross-validation leakage controls, and execution realism checks so every AlphaForge run produces statistically defensible validation artifacts, enforces promotion gates, and surfaces rich visualization payloads to Mind.

Phase 3.5 (2025-10-11): Property-based permutation safeguards, documentation refresh (README, TESTING, quickstart, Mind guide), validation smoke artifacts, backfill playbook, and Masters retention policy landed. Governance hand-off now has gating criteria, waiver workflow, and SLA tracking (current total validation runtime 1543 ms vs 34 ms guardrail).

## Technical Context
**Language/Version**: Python 3.11 (Brain), TypeScript 5 / React 18 (Mind)
**Primary Dependencies**: FastAPI, Pydantic, NumPy, Pandas, Statsmodels, SciPy, SQLite/SQLAlchemy, SSE-Starlette; Mind consumes via React Query + Vite stack
**Storage**: SQLite for manifests + validation tables, Parquet/Arrow for run artifacts
**Testing**: Pytest (+pytest-asyncio, Hypothesis) for Brain, Vitest + Playwright contract tests for Mind
**Target Platform**: Backend services on deterministic Linux containers (CI + Docker), Mind deployed via Vite build targeting evergreen browsers
**Project Type**: brain+mind dual
**Performance Goals**: Keep permutation/cross-validation runtime within existing SLA (≤1.2× current run duration), SSE payloads ≤1.5 MB compressed, CI guard measuring validation stage runtime with 10% warning buffer
**Constraints**: Deterministic seed derivation, dual-root separation, contract versioning, back-compat for historical runs, no additional external services without waiver
**Scale/Scope**: Thousands of strategy runs/day, permutations per run O(10^2–10^3), cross-validation folds up to 10× CPCV combinations

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Determinism: PASS — reuse run seed root to derive permutation/cross-validation seeds; log seeds + counts in manifest.
- Test-First: PASS — plan to add failing tests covering new validation outputs (permutation summary endpoints, DSR/PSR calculations, CPCV leakage reporting, Mind visualization contracts).
- Modular MVC / Dual Root: PASS — Brain handles computation/persistence/API; Mind restricted to consuming payloads + toggles.
- Observability: PASS — extend existing validation span to include permutation, cross-validation, execution realism timings and SSR logging.
- Contract Versioning: PASS — additive API/SSE schema fields guarded with version bump + neutral defaults for legacy runs.
- Performance Targets: PASS — benchmark permutation + cross-validation runtime, reuse existing guardrail harness, add SLA thresholds.
- Data Integrity: PASS — schema extensions controlled via Alembic migration and manifest version update while preserving historical rows.

Re-evaluated after Phase 1 design → status unchanged (PASS).

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

**Structure Decision**: Option 4 — Dual Project (AlphaForge Brain + AlphaForge Mind); requires contract updates for validation payload schemas.

## Phase 0: Outline & Research
- Catalog existing validation engines (current metrics, permutation stubs) and identify integration points in Brain services.
- Survey Masters permutation methodology, DSR/PSR, CSCV, Purged K-Fold/CPCV literature and map to deterministic implementation steps.
- Inventory current persistence schema (SQLite tables, manifests) and determine extension strategy for new validation metadata.
- Audit API/SSE payload generators and Mind data adapters to understand serialization/consumption expectations.
- Assess execution realism models already present (transaction costs, liquidity) to avoid double counting.

## Phase 1: Design & Contracts
- Draft Brain module design: permutation orchestrator, validation configuration toggles, runtime scheduler, execution realism integration hooks.
- Define deterministic seed derivation strategy and state machine for permutations/cross-validation.
- Establish CSCV bias flag rule: mark runs when CSCV-adjusted Sharpe ≤ observed Sharpe − 0.25 or drops by ≥20% relative.
- Fix default purge span policy: embargo windows default to max(30 calendar days, strategy lookback) to align with Masters methodology, overridable via config.
- Specify execution realism guidance payload (cost/impact deltas, capacity ratio, remediation recommendations) for API/UI parity.
- Specify SQLite schema extensions, manifest updates, and artifact storage layout (histograms, diagnostics).
- Produce Mind contract schemas (permutation distribution series, Sharpe adjustment summaries, fold diagnostics, realism alerts) with versioned OpenAPI references.
- Document CLI/SDK configuration surfaces for enabling/disabling validation modules and retrieving metadata.

## Phase 2: Task Planning Approach
Generate tasks grouped by:
- Brain: research tests first, implement permutation engine, Sharpe deflation calculations, cross-validation modes, execution realism integration, persistence + API exposure, benchmarking harness updates.
- Mind: contract fixtures, visualization components, toggles, SSE stream updates, explanatory copy.
- Shared/Docs: OpenAPI, README/TESTING updates, migration notes, quickstart validation walkthrough.
Each task will tag affected root (Brain/Mind/shared/docs) and reference relevant FR IDs.

## Phase 3+: Future Implementation
[Same]

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Implementation complete (Brain + Mind waves merged; polish tasks T043–T047 incorporated)
- [ ] Phase 4: Validation & governance sign-off in progress (SLA tuning outstanding)
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v1.1.0 - See `/memory/constitution.md`*
