
# Implementation Plan: Elevate Project A to Truthful Backtest Simulator (Truthful Run Foundation)

**Branch**: `003-elevate-project-a` | **Date**: 2025-09-22 | **Spec**: `specs/003-elevate-project-a/spec.md`
**Input**: Feature specification from `C:/Users/amasr/AlphaForge3/specs/003-elevate-project-a/spec.md`

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
Deliver a staging-quality, deterministic, causality-enforced single-asset backtest execution loop for NVDA with: dataset validation & provenance hashing, feature materialization (with optional global +1 shift), guarded strategy signal evaluation (strict runtime future access guard), realistic-but-minimal execution cost modeling (slippage, fees, borrow), trade ledger + PnL attribution, statistical validation sentinel (permutation test), deterministic artifact pack (manifest, metrics, validation, equity.parquet, trades.parquet, plots.png) and stable idempotent API (POST /runs, GET /runs/{id}, SSE events). This plan details Phase 0 (research) & Phase 1 (design/contracts) outputs and readies Phase 2 task generation.

Primary success criteria:
1. Identical run config + dataset snapshot yields identical run & artifact hashes (Principle 1).
2. No look-ahead: zero recorded future access violations in strict mode for baseline strategies.
3. Permutation test produces reproducible distribution given seed; p-value surfaced in summary & events.
4. All functional requirements FR-001..FR-041 mapped to design entities, API contracts, or test plans.
5. Constitution checks pass with no unjustified complexity.

Non-functional goals:
- Determinism: Float serialization (precision=8), stable plot rendering, seed management.
- Observability: Structured events & summary snapshot with anomalies subset & validation counters.
- Extensibility groundwork: Clear seams for future multi-symbol & advanced execution without premature abstraction.

Out-of-scope (kept minimal): partial fills, multi-asset portfolio, cancellation endpoint (deferred), advanced walk-forward validation.

## Technical Context
**Language/Version**: Python 3.11 (Constitution Additional Constraints #1)  
**Primary Dependencies**: FastAPI (API), Pydantic (schemas), numpy/pandas (data/metrics), matplotlib (plots), typing/mypy, ruff, pytest  
**Storage**: Local filesystem artifacts (manifest + parquet + json) under run-specific directories; no DB  
**Testing**: pytest (unit, integration, contract), mypy strict type checks, spectral/OpenAPI diff for contract  
**Target Platform**: Linux & Windows dev parity via Docker and local Python; containerized CI  
**Project Type**: Single backend domain-oriented Python service (no separate frontend)  
**Performance Goals**: Baseline single-symbol NVDA 5-year run completes < 5s on dev machine; permutation N=100 < 30s (parallel seeds); guard overhead <1% (ISSUE-GUARD-001 acceptance)  
**Constraints**: Deterministic seeds; no nondeterministic multithreading; SSE heartbeat ≤15s; memory footprint <1GB for 5-year daily (ample headroom)  
**Scale/Scope**: Single asset initial; baseline for future multi-asset & orchestration  

No remaining NEEDS CLARIFICATION markers—guard mode, float precision, versioning resolved.

## Constitution Check
Initial Assessment (Pre-Phase 0):
- P1 Deterministic Reproducibility: Addressed via run hash, dataset hash, artifact hashing (FR-001, FR-015, FR-023, FR-024, FR-041) — OK.
- P2 Additive Evolution: OpenAPI version ties to package (FR-031); no breaking removals — OK.
- P3 Test-First: Plan mandates contract + guard violation tests before implementation — OK.
- P4 Data Integrity: Validation artifact + anomaly counters (FR-002, FR-003, FR-030) — OK.
- P5 Modular Architecture: Entities segmented (data/feature/strategy/execution/validation) — OK.
- P6 Observability: SSE phases, metrics, anomaly counts, summary snapshot (FR-013, FR-018, FR-036) — OK.
- P7 Performance Guardrail: Explicit baseline target + guard overhead limit — OK.
- P8 Avoid Speculative Complexity: Defers partial fills, cancellation endpoint (FR-025 SHOULD, ISSUE-CANCEL-001) — OK.
- P9 Single Source of Truth: Manifest is canonical; OpenAPI version from package — OK.
- P10 Tooling & Typing: mypy strict, no new ignores; contract diff gating planned — OK.

No violations requiring justification. Post-Design re-check scheduled after Phase 1 artifacts.

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
6. (Added Gate) Zero mypy errors & no unjustified `# type: ignore` comments before exposing API endpoints (Phase 3.4H Type Hygiene Gate).

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

**Constraints**: Determinism: Float serialization (precision=8), stable plot rendering, seed management. Pre-API Type Hygiene Gate (Phase 3.4H) required.
api/
└── [same as backend above]
**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 4H**: Type Hygiene Gate (inserted between service completion & API exposure)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)
└── [platform-specific structure]
```

**Structure Decision**: Option 1 (Single project) — current repo already domain-structured under `src/`; no split needed.

 - [x] Type Hygiene Gate (Phase 3.4H) COMPLETED (zero mypy errors, no unjustified ignores) — API tasks may proceed (CI enforced)
## Phase 0: Outline & Research
Resolved Unknowns (captured from spec clarifications):
- Future data access validation approach → runtime strict guard (ISSUE-GUARD-001).
- Float determinism precision → precision=8 fixed format (FR-041).
- API versioning scope → Phase 1 tied to package; future headers deferred (ISSUE-API-VERS-001).
- Cancellation semantics → deferred (ISSUE-CANCEL-001) pending orchestrator maturity.

Research Topics & Findings (to be elaborated in `research.md`):
1. Causality Guard Patterns: DataFrame window proxy vs slice copying (choose proxy for zero-copy + constant time checks). Alternatives: AST static analysis (deferred) / monkeypatch global objects (rejected: fragility).
2. Deterministic Plot Rendering: Matplotlib rcParams lock vs custom backend; choose rcParams & 'Agg'; alternative caching layer unnecessary now.
3. Permutation Parallelism: Precomputed seed list & post-sort vs deterministic job scheduler; choose seed list (simpler, reproducible order). Alternative: joblib random backend (extra dependency, nondeterministic ordering risk).
4. Borrow Cost Accrual: Per-bar linear accrual vs continuous compounding; choose linear for transparency; log potential extension.
5. Idempotent Run Hash Inputs: Canonical serialization ordering (sorted keys JSON) vs pickle; choose JSON canonicalization (readable, stable). Alternative: protobuf (extra layer not needed yet).

Planned `research.md` Sections:
- Decisions Table (each of 5 topics above)
- Rationale & Alternatives
- Open Future Considerations (multi-asset, advanced execution)

Gate: All prior unknowns resolved — proceed to Phase 1.

## Phase 1: Design & Contracts
Deliverables to produce now:
1. `data-model.md` — Entities & Schemas
   - DatasetSnapshot: path, data_hash, calendar_id, bar_count, first_ts, last_ts
   - FeatureSpec: name, version, shift_applied(bool), inputs, params
   - StrategyConfig: id, required_features[list], parameters[dict]
   - ExecutionConfig: fill_policy(enum), lot_size, rounding_mode
   - CostModelConfig: slippage_bps, spread_pct|participation(optional), fee_bps, borrow_cost_bps
   - RunConfig: dataset_ref, strategy_config, feature_specs, execution_config, cost_model_config, validation(permutation_trials, seed), causality_shift(bool)
   - Trade: ts, side, qty, pre_cost_price, exec_price, slippage_components, fee_bps, borrow_accrued, position_after, cash_after, hash(optional)
   - EquityBar: ts, equity, realized_pnl, unrealized_pnl, cost_drag, position
   - ValidationResult: permutation_observed, permutation_distribution_hash, p_value, trials
   - RunManifest: run_id, run_hash, config_hash, dataset_hash, seeds, created_at, artifacts[], chain_prev(optional), float_precision, api_version
   - SummarySnapshot: run_id, phase, progress_pct, trades, final_equity(optional), p_value(optional), anomalies(optional)
   - CausalityViolationMetric: violations_count (0 expected)

2. `contracts/` contents
   - `runs.post.json`: Request schema (RunConfig), Response { run_id, run_hash, status, created_at }
   - `runs.get.json`: Response { run_id, status, phase, artifacts[], summary (subset) }
   - `runs.events.sse.md`: Event types (heartbeat, phase_transition, summary_snapshot, terminal)
   - `versioning.md`: Phase 1 policy & triggers for future phases referencing ISSUE-API-VERS-001

3. Contract Tests (placeholders; failing initially):
   - `tests/contract/test_post_runs.py`
   - `tests/contract/test_get_runs.py`
   - `tests/contract/test_runs_events_sse.py`
   Each asserts schema keys & deterministic ordering constraints.

4. `quickstart.md` — Steps to: (a) prepare dataset, (b) submit run, (c) tail SSE, (d) inspect artifacts, (e) verify determinism by re-run hash equality.

5. Update agent context (script invocation deferred until after files added).

Design Notes:
- Guard Implementation: Provide `CausalAccessor[T]` wrapping Series/DataFrame slices with index fence; raising `FutureDataAccessError` in strict mode.
- Hashing Canonicalization: Stable JSON dumps with sort_keys=True & separators to ensure identical config_hash generation.
- Parallel Permutation: Precompute seeds list -> spawn tasks -> gather -> order -> hash distribution via stable tuple of floats (rounded to precision=8) before writing.
- Plot Determinism: Dedicated `plot_equity.py` module with deterministic style initializer invoked once per run.

Post-Design Constitution Re-check planned after artifact creation.

## Phase 2: Task Planning Approach
*Description only (tasks.md will be generated separately).* Remains aligned with template; each entity & endpoint yields test-first tasks; guard & permutation parallelism flagged as early tasks due to foundational nature.

## Gap Coverage & Assurance Matrix
User-highlighted gaps and how they are addressed in spec & plan. New issue placeholders added where future work is required beyond truthful baseline scope.

| Gap | Current Coverage (FR / Artifact) | Residual Risk | Action / Issue |
|-----|----------------------------------|---------------|----------------|
| Execution simulator (fills, costs, spread) not wired | FR-007 (fill timing), FR-008 (costs: slippage/fees/borrow + extended slippage inputs), FR-009..FR-011 (lot, ledger, PnL), FR-039 (borrow formula); `data-model.md` Trade & EquityBar entities | Latency modeling absent (order delay), advanced spread dynamics simplified | Treat latency as deferred realism enhancement → ISSUE-LAT-001 created (document requirement & benchmarks) |
| Validation breadth & overfit risk | Permutation + walk-forward (FR-019..FR-022, FR-046..FR-048) | Adaptive/meta layer not yet present | ISSUE-VAL-ADAPT-001 future enhancement |
| Run manifests & checksums missing | FR-001 (dataset hash), FR-015 (manifest fields), FR-023 (artifact hashing), FR-024 (replay determinism), FR-041 (float policy); `data-model.md` RunManifest | Implementation must ensure stable canonical serialization & environment capture (library versions) | Explicit task: implement `config_hash` + environment capture; verify hash reproducibility test (will appear in tasks.md) |
| Observability: SSE events not shipping | FR-018 (SSE endpoints), FR-026 (phase ordering), FR-032 (terminal event), FR-036 (anomalies snapshot); `contracts/runs.events.sse.md` | Need concrete emitter & heartbeat scheduler; risk of silent stall if heartbeat fails | Add explicit tasks for emitter layer + watchdog test. SSE contract already includes artifact listing in terminal event. |
| Latency realism (order delay, queue) | Not in baseline FR list (intent is minimal truthful core) | Potential optimism in slippage modeling if strategy depends on intrabar latency | ISSUE-LAT-001 (deferred). Document in README realism backlog. |
| Robustness reporting clarity | FR-047 (p-value, tails, stability) | Misinterpretation if undocumented | Quickstart doc section + schema tests |
| Permutation engine structural fidelity | FR-042 (gap preservation, relative transforms) | Subtle leakage if absolute prices shuffled | Add invariant tests (distribution length, gap positions, no NaN) |
| Significance breadth (tail metrics) | FR-043 (extreme_tail_ratio) | Misinterpret borderline p without tail context | Add metrics schema test asserting field presence |
| Permutation scalability (1000+ trials) | FR-044 (pluggable backend) | Performance bottleneck without parallelism | ISSUE-DIST-PERM-001 deferred distributed backend |
| Strategy registry bias mitigation | FR-045 (accept/reject metadata) | Survivorship / graveyard bias risk | ISSUE-STRAT-REG-001 governance & audit trail (future) |
| Walk-forward infra implementation | FR-046 (MUST) | Complexity & config mis-spec | ISSUE-VAL-WF-001 tracks implementation |
| Bias-preventive splits enforcement | FR-048 (MUST) | Overlap/leakage risk | ISSUE-VAL-SPLIT-001 guard tests |

### New Issue Placeholders
#### ISSUE-LAT-001: Latency & Order Delay Modeling
Scope: Introduce configurable order delay (N bars or millisecond offset for intraday), optional queue simulation, and latency-aware fill price adjustments.
Acceptance: Deterministic configuration yields reproducible adjusted fills; performance overhead <5%; metrics include latency_impact.
Status: Deferred (post truthful baseline).

#### ISSUE-VAL-WF-001: Walk-Forward Validation (MUST)
Scope: Rolling window re-fit & evaluation segments (train/test splits) with aggregated performance distribution and stability metrics.
Acceptance: Manifest records segment definitions; metrics include mean & variance & proportion_of_profitable_oos_segments; deterministic segmentation; walk_forward.json emitted when enabled.
Status: In-scope.

#### ISSUE-VAL-ROB-001: Robustness & Hypothesis Reporting (MUST)
Scope: Aggregate p_value, extreme_tail_ratio, OOS dispersion (consistency score), composite robustness_score exposed in summary & artifacts.
Acceptance: Summary includes fields; data-model & quickstart updated; tests assert presence & deterministic rounding.
Status: In-scope.

#### ISSUE-VAL-SPLIT-001: Bias-Preventive Temporal Splits (MUST)
Scope: Enforce non-overlapping chronological train/test per segment (optional warm-up). Reject invalid overlaps & backwards ranges.
Acceptance: Invalid config raises validation error; manifest includes precise timestamps per segment; tests cover edge boundaries.
Status: In-scope.

#### ISSUE-VAL-HO-001: Holdout / Out-of-Sample Segment (Future)
Scope: Reserve terminal date range as untouched validation slice; primary metrics reported separately.
Acceptance: Manifest records holdout boundaries; summary includes oos_{metric} fields; no leakage in feature construction.
Status: Deferred.

#### ISSUE-DIST-PERM-001: Distributed / Cluster Permutation Backend (Future)
Scope: Executor abstraction for remote multi-worker trial execution while reproducing deterministic sorted distribution.
Acceptance: Same ordered distribution & hash as local backend; scale test 100→1000 trials <10x wall time.
Status: Deferred.

#### ISSUE-STRAT-REG-001: Strategy Registry Governance & Bias Mitigation (Future)

#### ISSUE-VAL-ADAPT-001: Adaptive / Meta Validation Layer (Future FR-049)
Scope: Meta-evaluation across runs incorporating adaptive segment sizing, regime-aware rolling validation.
Acceptance: Design doc & prototype stage before promotion to MUST.
Status: Future.
Scope: Central registry of all evaluated strategies (id, param_hash, acceptance_reason, rejection_reason, decision_ts). API & manifest cross-link.
Acceptance: Registry query returns complete audit trail; no orphan strategy config used in runs without registry entry.
Status: Tracking.

### Summary
All user-stated baseline gaps are either covered by existing FRs/entities or explicitly deferred with issue tracking and acceptance criteria defined. No additional MUST FRs added for latency to avoid speculative complexity (Principle 8); instead, clear extension path documented.

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
No deviations from Constitution principles; table intentionally empty.


## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS (to be marked after artifacts created)
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v1.2.0 - See `.specify/memory/constitution.md`*
