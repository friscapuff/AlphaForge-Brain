# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure (single, web, mobile, dual brain+mind)
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services/controllers, views (frontend) respecting MVC
   → Integration: DB, middleware, logging, cross-project contract adapters
   → Polish: unit tests, performance, docs, benchmarks
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests
   → All entities have models
   → Cross-project contracts have version bump tasks if breaking
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- For dual project: prefix with (brain) or (mind) root

## Path Conventions
- **Single project**: `src/`, `tests/`
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- **Dual Project (Brain + Mind)**:
  - `alphaforge-brain/src/` (models, services, persistence, analytics)
  - `alphaforge-mind/src/` (ui components, view adapters, controllers)
  - `shared/` (pure utilities only; no side-effects)

## Phase 3.1: Setup
- [ ] T001 Create/confirm project structure per plan (respect dual root if selected)
- [ ] T002 Initialize dependencies in appropriate root(s)
- [ ] T003 [P] Configure linting, type checking, formatting

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
- [ ] T004 [P] Contract test(s) for brain service API (if any) in tests/contract/
- [ ] T005 [P] Integration test cross-project contract (if dual) in tests/integration/
- [ ] T006 [P] Mind UI interaction test skeleton (if frontend present)
- [ ] T007 [P] Determinism/seed fixture tests

## Phase 3.3: Core Implementation
- [ ] T008 [P] (brain) Domain model(s)
- [ ] T009 [P] (brain) Service/controller logic
- [ ] T010 [P] (mind) View component(s)
- [ ] T011 (brain) Public API/adapter endpoint(s)
- [ ] T012 (mind) Adapter consuming brain contract
- [ ] T013 Validation & input schema layer
- [ ] T014 Error handling & logging integration

## Phase 3.4: Integration
- [ ] T015 Persistence / migrations
- [ ] T016 Auth / security middleware
- [ ] T017 Observability instrumentation (timing + tracing)
- [ ] T018 Cross-project contract version file & negotiation logic (if dual)

## Phase 3.5: Polish
- [ ] T019 [P] Additional unit tests (edge cases)
- [ ] T020 Performance / benchmark tests
- [ ] T021 [P] Update docs/contracts & README
- [ ] T022 Remove duplication / refactor
- [ ] T023 Run quickstart validation script

## Dependencies
- Tests (T004–T007) precede implementation (T008–T014)
- T008 blocks T009; T009 may block T011
- Dual integration (T018) requires T011 + T012

## Parallel Example
```
Launch T004–T007 concurrently (independent files) before any implementation.
```

## Notes
- For dual root architecture, enforce no direct imports from mind → brain except via defined contract modules (or API clients)
- [P] tasks MUST not modify same file
- Contract changes require version bump reasoning

## Validation Checklist
- [ ] All contracts have tests
- [ ] All entities have model tasks
- [ ] Tests precede implementation
- [ ] Parallel tasks independent
- [ ] No cross-root forbidden imports
- [ ] Version impact documented for contracts
