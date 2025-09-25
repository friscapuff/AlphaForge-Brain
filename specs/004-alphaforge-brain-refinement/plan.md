# Implementation Plan: AlphaForge Brain Refinement (Persistence, Causality & Statistical Breadth)

**Branch**: `004-alphaforge-brain-refinement` | **Date**: 2025-09-23 | **Spec**: `spec.md`
**Input**: Feature specification at `C:/Users/amasr/AlphaForge3/specs/004-alphaforge-brain-refinement/spec.md`

## Phase -1: Architecture Migration Gate (MANDATORY BEFORE ANY OTHER PHASE)
Objective: Transition repository from single-root (`src/`, `tests/`) to dual root scaffold (Brain backend + Mind placeholder) while preserving determinism and passing all existing tests.

Tasks (summary; full detail will be in tasks.md Gate A section):
1. Create directories: `alphaforge-brain/src/`, `alphaforge-brain/tests/`, `alphaforge-mind/src/` (placeholder), `alphaforge-mind/tests/`, `shared/`.
2. Move existing backend code & tests into `alphaforge-brain/` preserving package namespace (`alphaforge_brain`).
3. Update import paths, mypy/pytest/ruff configs; add transitional shim only if needed (document waiver).
4. Add cross-root integrity script (`scripts/ci/check_cross_root.py`) failing on forbidden imports.
5. Add `WAIVERS.md` with process & template; no waivers active post-migration ideally.
6. Run determinism baseline test before move; repeat after move (hash equality).
7. Update README to reflect new structure & architecture diagram reference.
8. Remove legacy `src/` once imports updated.

Exit Criteria (all required to proceed):
- Tests pass and determinism replay unchanged.
- No direct imports referencing removed legacy path.
- Integrity script passes.
- README + constitution both reference dual root.

---

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
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
Add durable SQLite persistence + provenance, hardened causality guard, broadened statistical validation (adaptive block bootstrap + extended walk-forward), and memory & performance optimizations (feature store caching, chunked rolling compute, float32 dietary column strategy, vectorized/numba indicators, Parquet/Arrow ingestion) while preserving strict determinism and reproducibility. Emphasis on controlling data footprint, avoiding recomputation, and providing a versioned feature cache keyed by dataset + indicator specification.

## Technical Context
**Language/Version**: Python 3.11
**Primary Dependencies**: pandas, numpy, numba (new), pyarrow, FastAPI (existing for service endpoints), sqlite3 / SQLAlchemy-lite helper (if needed, but avoid ORM), ruff, mypy, pytest
**Storage**: SQLite (primary), Parquet (feature & raw data cache), JSON artifacts (hash-canonical), in-memory DataFrames
**Testing**: pytest (unit, integration, contract), hash-based golden tests for determinism
**Target Platform**: Local dev & CI (Windows + Linux runners)
**Project Type**: Single-project backend/analysis library (Option 1 structure)
**Performance Goals**: ≥50k rows/sec bulk insert; bootstrap runtime ≤1.2x IID baseline; memory reduction for feature pipeline via float32 + chunked build (target ≥25% lower peak RSS)
**Constraints**: Deterministic seeding (seed=sha256(config_json)%2**32); monotonic single-symbol index; no MultiIndex; no chained indexing; minimal copying
**Scale/Scope**: Up to ~0.5M bars baseline; engineered headroom multi-million rows; bootstrap trials default 1000 local / 200 CI

Additional Provided Strategies (User Input Integration):
1. Data Footprint Diet: enforce dtypes (int64 ns timestamp, OHLC float32, volume int64, feature_* float32)
2. Versioned Feature Store: key = hash(dataset)+indicator_name+version+params; Parquet + SQLite metadata row
3. Chunked Rolling & Joins: windowed processing with overlap window-1; staged merges
4. Numba/Vectorized Indicators: rewrite hot paths (SMA, volatility, drawdown) to array kernels
5. Arrow/Parquet IO + optional memory mapping for selective column load
6. Orchestrated Sweeps: single feature compute then many strategies (write-once read-many)
7. Deterministic Reproducibility: config hash → seed root, propagate to bootstrap & permutation

## Constitution Check
The constitution file is a placeholder (principle identifiers not yet populated). Interim interpretation:
Principles enforced implicitly via: determinism, test-first, simplicity (no extraneous frameworks), observability, provenance.
No violations introduced by planned approach:
- Library-first: All additions reside in existing `src/` modules (no new project boundary).
- Test-first: Acceptance test stubs already enumerated (bootstrap, causality, persistence, feature cache).
- Observability: Phase includes timing spans & error logging (aligned with principle of structured insight).
Pending until constitution filled with concrete rule names; mark Initial Constitution Check: PASS (provisional).

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 1 (single project) — no multi-tier web/mobile complexity required.

## Phase 0: Outline & Research
Focus: lock in low-level strategy choices & benchmarks baseline design.

Research Tracks:
1. Block Length Heuristic Validation: empirical ACF on synthetic + real sample; confirm cap (<=50) adequate.
2. Float32 Precision Impact: Sharpe/CAGR deviation vs float64 (<1e-4 relative acceptable) across sample runs.
3. Numba Feasibility: Evaluate compile time overhead vs speedup for SMA/volatility on 1M rows.
4. Parquet IO Profile: pyarrow column-select vs pandas read_csv baseline timing & memory.
5. SQLite Bulk Insert Modes: WAL vs normal; executemany vs batched copy; measure rows/sec.
6. Feature Cache Key Stability: Hash function collision probability (sha256) & deterministic ordering of params.
7. Chunk Overlap Correctness: Rolling window edge validation — confirm no discontinuity at boundaries.

Deliverable (`research.md`) Sections:
- Decisions (per track)
- Rationale
- Alternatives Considered
- Benchmarks (table)
- Open Follow-ups (should be zero blocking items before Phase 1)

Exit Criteria: All FR preconditions satisfied; no unresolved research blockers; provisional PASS constitution.

## Phase 1: Design & Contracts
Prerequisite: `research.md` complete and accepted.

Design Outputs:
1. `data-model.md` — Entities & Fields:
   - Run, Trade, Equity, Validation, FeaturesCacheMeta, PhaseMetric, RunError
   - Explicit dtypes: timestamp int64(ns), OHLC float32, volume int64, feature_* float32
2. `contracts/`:
   - (If service endpoints exist) Minimal API surface for retrieving run summary & validation metrics (read-only) — FastAPI path specs (internal use).
   - Feature cache manifest schema (JSON Schema) for key metadata.
3. `quickstart.md`:
   - Steps: ingest data (Parquet) → feature cache build (or hit) → run simulation with bootstrap → inspect SQLite + query example → validate determinism.
4. Contract Tests (failing initially):
   - Feature cache retrieval populates metadata fields.
   - Deterministic seed reproduction test skeleton.
   - Bootstrap method metadata presence test.
5. Agent Context Update: run update script (if present) to capture new tech (numba, pyarrow, Parquet caching) succinctly.

Exit Criteria: All schemas documented, contract tests in place (failing), quickstart provides reproducible path.

## Phase 2: Task Planning Approach
Will partition tasks by phases:
Phase A (Schema & Migration), Phase B (Causality Guard), Phase C (Feature Cache + IO), Phase D (Statistical Breadth Bootstrap Engine), Phase E (Chunked Pipeline & Numba Indicators), Phase F (CI & Determinism Gates), Phase G (Docs & Cleanup). `/tasks` command will generate tasks grouped & ordered with parallelizable tags [P] where side-effect isolation exists (e.g., independent indicator kernels).

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
No constitution violations identified (placeholder constitution). All complexity additions (feature cache, bootstrap method, chunked iterator) directly trace to FRs & performance goals.


## Progress Tracking
**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning described (/plan command)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (provisional)
- [ ] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
