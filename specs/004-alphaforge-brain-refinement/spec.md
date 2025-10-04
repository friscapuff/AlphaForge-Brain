# Feature Specification: AlphaForge Brain Refinement (Persistence, Causality & Statistical Breadth)

**Feature Branch**: `004-alphaforge-brain-refinement`
**Created**: 2025-09-23
**Status**: Draft (Planning Phase – pending acceptance)
**Input Summary**: Extend truthful simulator (Spec 003) with durable persistence (SQLite), hardened causality guard, broadened statistical validation (bootstrap + enriched walk-forward), memory-conscious feature pipeline, and artifact provenance upgrades while preserving strict determinism.

## 🔰 Architecture Migration Gate (Must Complete Before Any Phase A Work)
This feature now depends on transitioning from a single-root layout (`src/`, `tests/`) to a dual-project scaffold (Brain backend vs future Mind frontend). Implementation of persistence & statistical breadth MUST wait until these migration tasks are complete.

Migration Objectives:
- Introduce directory skeleton:
  - `alphaforge-brain/src/`, `alphaforge-brain/tests/`
  - `alphaforge-mind/src/` (placeholder), `alphaforge-mind/tests/` (placeholder)
  - `shared/` (optional pure utilities only)
- Move existing backend code from `src/` → `alphaforge-brain/src/`; tests to `alphaforge-brain/tests/`.
- Add transitional shim (optional) or direct import refactors; ensure all imports reference new namespace.
- Add cross-root integrity script disallowing reverse imports or Mind→Brain direct coupling beyond contracts.
- Update tooling configs (mypy, pytest, ruff) paths.
- Add `WAIVERS.md` for future temporary principle exceptions.
- Validate determinism equivalence: run representative tests & hash a baseline run pre- and post-move.

Migration Exit Criteria (Gate PASS):
1. All Python package imports updated to `alphaforge_brain` root; no stale `from src...` patterns.
2. CI and local test runs pass identical determinism test (two-run hash equality) before and after move.
3. Cross-root integrity script passes (no forbidden imports; Mind stub clean).
4. README updated to reflect dual-root; constitution already at v1.2.0.
5. Legacy `src/` directory removed (unless intentionally left as temporary shim documented in WAIVERS.md with expiry).

On Gate PASS, continue with FR implementation phases (Persistence, Causality, Statistical Breadth, etc.).

---

## Execution Flow (spec authoring)
```
1. Parse refinement intent vs Spec 003 deliverables
2. Identify delta scope (persistence, causality runtime guard, statistical breadth, pipeline efficiency)
3. Collect user stories & acceptance tests
4. Generate Functional Requirements (incremental; avoid re-listing Spec 003 FRs unless extended)
5. Define persistence schema & data contracts
6. Enumerate risks, success metrics
7. Clarify open questions → mark [NEEDS CLARIFICATION] if any
8. Produce planning tasks pre-implementation
9. Review checklist gating Implementation
```

---

## ⚡ Quick Guidelines
- ✅ Focus on DELTA relative to Spec 003 (do not restate baseline truthful simulator requirements)
- ✅ Emphasize persistence, causality guard strengthening, statistical robustness, memory scalability
- ❌ Avoid low-level module internals beyond contracts & schema
- 📎 All new FR IDs start at 100+ to avoid collision with earlier specs

### Ambiguity Handling Policy
Any uncertainty appears with [NEEDS CLARIFICATION]; none may advance to implementation until resolved or formally deferred with an ISSUE stub.

---

## Delta Problem Statement
While Spec 003 achieved deterministic, causality-shifted, artifact-rich single-equity simulation, several gaps inhibit scaling and audit depth: (a) no durable queryable store (filesystem-only artifacts), (b) runtime guard for future data access not yet enforced, (c) statistical inference limited to permutation test only, (d) feature build is monolithic raising memory concerns for larger universes or higher-frequency data, (e) provenance chain lacks persistence versioning & bootstrap/walk-forward context, and (f) CI surface does not yet enforce statistical stability or schema drift.

---

## User Scenarios & Acceptance (Delta)
1. As a quant reviewer, I can retrieve run metrics, equity, and trades from SQLite by run hash after artifacts have been moved/archived, ensuring long-term audit durability.
2. As a strategy developer, if I accidentally write a feature referencing future bars, the run aborts (STRICT) and metrics show zero persisted results, with a clear causality violation message.
3. As a risk analyst, I can inspect bootstrap confidence intervals and see them embedded next to Sharpe and CAGR, with configurable CI width gating.
4. As a performance engineer, I can enable chunked feature build and observe materially lower peak memory without hash deviation in outputs.
5. As a platform maintainer, I can run two identical runs and verify DB row hashes + artifact hashes stable; if schema changes without a migration script, CI fails.
6. As a research lead, I can review walk-forward aggregated robustness indicators (proportion profitable, OOS consistency) persisted both in validation and metrics outputs.

Edge / Negative Cases:
- Bootstrap disabled (trials=0) → CI width gate skipped gracefully.
- Causality guard PERMISSIVE mode counts >0 violations → metrics flag present; deterministic failure only in STRICT.
- Chunk size >= dataset length → falls back to original monolithic path (no performance regression).
- Migration file missing for schema delta → migration verification gate fails build.

---

## Functional Requirements (Delta Set)
These extend baseline truthful simulator; earlier FRs remain implicitly in force. IDs TIED to implementation tasks (see Planning), not to previous FR numbering.

### Persistence & Provenance
- **FR-100**: MUST introduce SQLite schema (tables: runs, trades, equity, metrics, validation, features_cache) with deterministic creation order & explicit `schema_version` recorded in a `meta` or manifest field.
- **FR-101**: MUST persist full manifest + config JSON in `runs` table atomically before heavy simulation; status transitions updated in-place.
- **FR-102**: MUST bulk insert trades & equity in a single transaction at finalize for consistency; partial failure rolls back that transaction while preserving earlier run row.
- **FR-103**: MUST add provenance fields: `db_version`, `bootstrap_seed`, `walk_forward_spec` (if used) to manifest & persisted run row.
- **FR-104**: MUST provide read helpers (query by run_hash) returning typed records for tests; no ad-hoc ORM complexity introduced.
- **FR-105**: MUST compute and record row counts per table for the run in metrics or manifest to enable replay validation.

### Causality & Determinism Hardening
- **FR-110**: MUST implement `CausalAccessContext` that raises on forward index access in STRICT mode; logs & counts in PERMISSIVE mode.
- **FR-111**: MUST surface `future_access_violations` metric (0 for valid strategies) and embed in summary and manifest.
- **FR-112**: MUST test t signal -> t+1 fill invariant across multiple fill policy configurations (open/next tick surrogate) and fail if violated.
- **FR-113**: MUST include guard activation + mode in run manifest for audit.

### Statistical Breadth
 - **FR-120**: MUST implement Hybrid Adaptive Discrete Jitter Block Bootstrap (HADJ-BB): adaptive block length heuristic, ±1 jitter at boundaries (deterministic), fallback to simple IID when low autocorrelation or short series.
 - **FR-121**: MUST integrate bootstrap distributions into metrics.json & validation.json with per-metric objects: `{metric, ci:[l,u], mean, std, trials, method, block_length, jitter, fallback}`.
- **FR-122**: MUST enforce optional CI width threshold gate (configurable) producing failure or warning based on mode.
- **FR-123**: MUST extend walk-forward output to compute OOS robustness indicators (proportion profitable, variability metric) and persist them.
 - **FR-124**: MUST persist bootstrap method metadata (method, block_length, jitter, fallback) (validation table columns or JSON) and expose via read helpers.

### Data Pipeline / Memory
- **FR-130**: MUST provide deterministic chunk iterator (size parameter) preserving index ordering; final DataFrame equal (hash) to monolithic build.
- **FR-131**: MUST allow feature builder to operate in chunk mode with no functional output differences (hash-based regression test).
- **FR-132**: SHOULD provide memory benchmark harness measuring peak RSS vs baseline; acceptance target 25% reduction configurable.

### Artifact & Integrity Enhancements
- **FR-140**: MUST canonicalize JSON writes using sorted keys & UTF-8; record content hash for each persisted JSON also in DB (runs table or metrics).
- **FR-141**: MUST validate extended manifest schema against JSON Schema file; failure aborts finalize.
- **FR-142**: MUST support SQLite round-trip replay test verifying that re-materialized artifacts from DB match on-disk hashes.

### CI & Tooling
- **FR-150**: MUST add migration verification script detecting schema drift without migration file; gate fails.
- **FR-151**: MUST integrate determinism replay (two-run hash + DB row equality) into CI job.
- **FR-152**: MUST add bootstrap CI width gate to CI pipeline.
- **FR-153**: SHOULD add automated schema dump artifact for diff review.
 - **FR-154**: MUST capture per-phase timing (start/end timestamps + duration_ms) as structured metrics persisted to DB.
 - **FR-155**: MUST emit lightweight tracing spans (phase identifiers + correlation id) enabling chronological reconstruction without external tracing infra.
 - **FR-156**: MUST create persistent `run_errors` storage for any raised exceptions (phase, error_code, message, stack_hash) prior to run failure propagation.
 - **FR-157**: SHOULD persist phase completion markers to support future resumable runs (resume implementation deferred; marker persistence in scope).
 - **FR-158**: SHOULD define a minimal credential provider interface (env var based) for future external data/broker APIs; no multi-user auth or secret persistence this phase.

### Documentation
- **FR-160**: MUST deliver contracts appendix documenting table schemas, manifest new fields, causality guard semantics.
- **FR-161**: MUST create persistence quickstart demonstrating run execution then SQL query introspection.
- **FR-162**: MUST update README with new validation (bootstrap + extended walk-forward) overview.

Open (Pending) Clarifications:
- None currently → if new during planning, mark explicitly.

---

## Key Entities (Delta Focus)
- **SQLite DB**: schema_version, metadata tables.
- **Run Row**: manifest_json, config_json, status timeline.
- **Trades / Equity Tables**: canonical numeric schema with index ordering by timestamp.
- **Validation Row**: combined permutation + bootstrap + walk-forward summary.
- **Features Cache Meta**: spec hash, row/column counts, build timestamp.
- **Causality Guard Context**: mode, violation counter, seed influence (none expected).

---

## Persistence Schema (Initial Draft)
```
runs(run_hash PK, created_at, updated_at, status, config_json, manifest_json, data_hash, seed_root, db_version, bootstrap_seed, walk_forward_spec_json)
trades(run_hash FK, ts, side, qty, entry_price, exit_price, cost_bps, borrow_cost, pnl, position_after)
equity(run_hash FK, ts, equity, drawdown, realized_pnl, unrealized_pnl, cost_drag)
metrics(run_hash FK, key, value, value_type, phase)
validation(run_hash FK, payload_json, permutation_pvalue, bootstrap_sharpe_low, bootstrap_sharpe_high, bootstrap_cagr_low, bootstrap_cagr_high, bootstrap_method, bootstrap_block_length, bootstrap_jitter, bootstrap_fallback)
features_cache(meta_hash PK, spec_json, built_at, rows, columns, digest)
run_errors(id PK, run_hash FK, ts, phase, error_code, message, stack_hash)
phase_metrics(id PK, run_hash FK, phase, started_at, ended_at, duration_ms, rows_processed, extra_json)
```
Indexes: `(trades.run_hash, trades.ts)`, `(equity.run_hash, equity.ts)`, `(metrics.run_hash, metrics.key)`.
Migration Approach: sequential migration files `V{n}__description.sql` + checksum; gate verifies expected head.

---

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Schema drift w/o migration | Inconsistent environments | Migration checksum gate (FR-150) |
| Bootstrap runtime inflation | Slower CI | Reduce trials under CI flag; parallelizable seeding |
| Guard false positives | Developer friction | Test harness & PERMISSIVE mode instrumentation |
| Chunk refactor divergence | Subtle output mismatch | Hash regression golden tests |
| Replay mismatch from DB | Loss of trust | Round-trip test (FR-142) early in suite |
| Observability overhead | Performance regression | Keep spans in-memory; optional disable flag |
| Error log growth | Storage bloat | Store stack hash + truncated message |
| Resume ambiguity | Misuse of partial state | Document markers as non-executable; resume deferred |
| Over-engineered auth (premature) | Wasted effort / complexity | Single-user scope + FR-158 minimal provider only |

---

## Success Metrics
- Determinism: second identical run → identical artifact & DB row content hashes (FR-151).
- Causality: `future_access_violations == 0` for baseline strategies.
- Statistical Breadth: Bootstrap CI width stored & below configured max for baseline scenario.
- Memory: ≥ target reduction (configurable) on synthetic large input using chunk mode.
- Documentation: Appendix + Quickstart merged, referenced in README TOC.
 - Observability: All phases emit timing spans; synthetic failure test populates `run_errors`; overhead <3% wall-clock.

---

## Review & Acceptance Checklist
- [ ] Delta scope clearly separated from prior spec
- [ ] All new FR IDs ≥ 100
- [ ] No unresolved [NEEDS CLARIFICATION]
- [ ] Persistence schema coherent & migration path stated
- [ ] Acceptance metrics measurable
- [ ] Risks have concrete mitigations

Gate: Only after all above checked may tasks transition from Planning to Implementation.

---

## Acceptance Test Stubs (FR-120–FR-124 Focus)
These are high-level test intentions; concrete test cases will be implemented under `tests/validation/` and `tests/integration/`.

1. AT-BS-001 (FR-120 baseline distribution):
	- Input: Deterministic small equity curve (seeded) with mild positive autocorrelation.
	- Expect: `method == "hadj_bb"`, `block_length` within heuristic bounds, `fallback == false`, Sharpe distribution size == trials.
2. AT-BS-002 (FR-120 fallback simple IID):
	- Input: Short series (length < 5 * heuristic block) or near-zero autocorrelation synthetic.
	- Expect: `method == "simple"`, `fallback == true`, block_length null.
3. AT-BS-003 (FR-121 metrics structure):
	- Expect: Per-metric objects contain keys: metric, ci, mean, std, trials, method, (block_length|None), jitter, fallback.
4. AT-BS-004 (FR-121 CI reproducibility):
	- Two identical runs (same seed) → identical CI endpoints & distributions hash.
5. AT-BS-005 (FR-122 CI width gate pass):
	- Config threshold > observed width → run passes; status success.
6. AT-BS-006 (FR-122 CI width gate fail):
	- Threshold < observed width in STRICT mode → run fails with explicit message.
7. AT-BS-007 (FR-123 walk-forward robustness integration):
	- Walk-forward enabled dataset → validation payload contains OOS proportion profitable & variability metric; values deterministic.
8. AT-BS-008 (FR-124 metadata persistence):
	- DB validation row columns (bootstrap_method, bootstrap_block_length, bootstrap_jitter, bootstrap_fallback) populated consistently with JSON payload.
9. AT-BS-009 (Cross FR-120–124 seed determinism):
	- Changing only trial count updates trials field but leaves method & block length stable (given same data) and distributions reproducibly truncated/extended.

Traceability: Each AT maps directly to FR-120–124 ensuring coverage of method selection, fallback, determinism, structure, gating, and persistence.

---

## Planning Tasks (Pre-Implementation Phase 0)
- [ ] T090 Confirm final FR set & resolve any late clarifications (none currently).
- [ ] T091 Draft JSON Schema for extended manifest (FR-141).
- [ ] T092 Draft migration framework scaffold + initial V1 script (FR-100).
- [ ] T093 Author regression hash test plan doc (golden tests for chunking & replay).
- [ ] T094 Approve CI additions outline (determinism replay, bootstrap gate).

Upon completion → mark Planning complete; proceed with Phases A–G tasks (renumbered remain T100+).

---

## Inline Issue Stubs
### ISSUE-PERSIST-001: Migration Verification Implementation
Tracks FR-150 migration checksum gate; failure mode behavior design.

### ISSUE-CAUSAL-001: CausalAccessContext Edge Performance
Benchmark overhead on large synthetic (1M rows) to ensure <1% slowdown.

### ISSUE-STATS-VERIF-001: HADJ-BB Validation & Performance
Validate adaptive block heuristic accuracy vs empirical ACF; benchmark jitter overhead (<20% over simple IID baseline for same trials) and confirm fallback triggers correctly.

---

## Future (Beyond This Spec)
- Multi-asset portfolio & scheduling engine
- Distributed permutation backend realization
- Advanced impact & borrowing term structure modeling
- Strategy governance & registry lifecycle enforcement

---
Generated 2025-09-23 (Spec 004 Draft – Delta oriented).

## Clarifications
### Session 2025-09-23
 - Q1: Target maximum dataset scale for this spec? → A: "Short combination of C & D" (interpreted as high-frequency multi-million row support: up to 1-minute bars for ~5 years single symbol, targeting tens of millions of rows headroom).
 - Q2: Required reliability & observability posture? → A: D (near production: tracing spans, persistent error log table, resumable run state expectation; resume execution itself deferred).
 - Q3: Security posture & user model? → A: Single personal user; future external data & broker APIs anticipated; minimal credential provider only.
 - Q4: Default bootstrap trials & CI level? → A: 1000 trials @ 95% CI (CI override 200 @ 90%).
 - Q5: Bootstrap method selection? → A: Adopt Hybrid Adaptive Discrete Jitter Block Bootstrap (HADJ-BB) with deterministic adaptive block length + ±1 jitter; fallback to simple IID under low autocorrelation or insufficient length.

### Applied Adjustments
 - Added explicit scale assumption to Success Metrics & Data Pipeline expectations.
 - Tuned design toward multi-million row resilience (chunk iterator heuristics + indexing guidance).
 - Added observability FRs (timing spans, error log table, phase metrics, resumable state markers stub).
 - Added security scope & bootstrap default policy (1000/95% local, 200/90% CI override) to inform FRs & benchmarks.
 - Selected HADJ-BB bootstrap method; updated FR-120/121 and added FR-124 + validation schema columns; documented fallback & determinism policy.

### Performance & Scale Assumptions
 - Upper bound design target: ~1-minute bars for 5 years single symbol (≈492k bars) with architectural headroom for multi-million rows (tens of millions) without redesign.
 - CI synthetic stress may simulate 2–5M rows for regression of chunk mode & persistence throughput.

### Non-Functional Targets
 - Bulk insert throughput goal: ≥ 50k rows/sec (equity + trades) on commodity dev hardware (adjust after first benchmark if unrealistic by >25%).
 - Bootstrap incremental memory: ≤ 25% additional peak over base dataset footprint for configured trial set (CI mode may downscale trials).
 - Chunk size heuristic: ~2–4% of total bars (bounded [25k, 250k]); user override allowed.
 - Observability overhead (timing + spans + error logging) < 3% added wall-clock vs baseline (benchmark required).
 - Bootstrap default: local 1000 trials @ 95% CI; CI override 200 @ 90% CI via env flag.
 - Bootstrap runtime target: ≤ 1.2x simple IID baseline for same trial count at typical dataset scale (first benchmark documents variance; adjust if >25% deviation).


---

## Clarification Coverage Summary
All five planned clarification domains resolved:
1. Scale & Dataset Headroom → Reflected in Performance & Scale Assumptions; chunk & indexing guidance embedded.
2. Reliability / Observability Level (D) → FR-154–158, success metrics line, schema additions (run_errors, phase_metrics).
3. Security / User Model (Single-user minimal credential provider) → Scoped via FR-158; deferred multi-user & secret persistence.
4. Bootstrap Trial & CI Policy → Defaults embedded (1000/95% local, 200/90% CI) in clarifications + non-functional targets.
5. Bootstrap Method Selection → HADJ-BB adopted; FR-120/121/124 + schema columns; fallback & determinism specified.

No outstanding [NEEDS CLARIFICATION] markers remain. Risks updated to reflect runtime considerations; selection issue replaced with verification issue (ISSUE-STATS-VERIF-001).

Recommendation: Mark Planning clarifications phase complete and proceed to finalize Planning Tasks (T090–T094) then transition into implementation phases.

---

## Addendum: Clarified Policies (2025-09-23)
These clarifications were added post-analysis to eliminate ambiguity prior to implementation.

### HADJ-BB Block Length Heuristic (FR-120)
Deterministic steps:
1. Let N = length of equity return series; L_cap = min(50, floor(N/4)).
2. Compute autocorrelation ACF(k) for k=1..L_cap using unbiased estimator.
3. Identify first local minimum k* where ACF(k*) < ACF(k*-1) and ACF(k*) < ACF(k*+1). If ACF(k*) < τ (τ=0.10) select k*.
4. If no such k* exists, choose k = L_cap.
5. Compute mean_abs_acf = mean(|ACF(1..k)|). If N < 5*k OR mean_abs_acf < 0.05 → fallback method = simple IID.
6. Jitter: deterministically compute j = ((seed_root + k) mod 3) - 1 producing {-1,0,+1}; effective_block = max(2, k + j).
7. Record: method="hadj_bb" unless fallback triggered; store block_length = effective_block, jitter=j, fallback boolean.

### CI Width Gating Policy (FR-122)
Monitored metrics: Sharpe, CAGR (initial). Compute width = ci_high - ci_low. Gate evaluation:
- STRICT mode: If ANY monitored metric width > threshold → run fails (status=failed; reason code CI_WIDTH_EXCEEDED).
- PERMISSIVE mode: Exceedances logged as warnings and manifest includes `ci_width_warnings` list.
Threshold provided via config; CI default narrower threshold may override env `BOOT_CI_WIDTH_MAX`.

### Multi-Window Chunk Overlap (FR-130/131)
Given rolling windows W = {w1, w2, ..., wm}, define overlap = max(W) - 1. Each chunk (except first) prepends last overlap rows from prior chunk. Feature functions must not forward-peek beyond available overlap. Multiple windows use the same overlapped slice; no individualized overlaps. Final chunk processes to end; no padding beyond dataset.

### Error Code Taxonomy (FR-156)
Prefix categories:
- PERSIST_* (e.g., PERSIST_MIGRATION_MISSING)
- CAUSAL_* (e.g., CAUSAL_FUTURE_ACCESS)
- STATS_* (e.g., STATS_CI_WIDTH_FAIL)
- PIPE_* (e.g., PIPE_CHUNK_MISMATCH)
- OBS_* (e.g., OBS_OVERHEAD_EXCEEDED)
- CI_* (legacy alias for STATS/DET gates if needed)
Codes recorded with snake case upper; stack_hash = sha256(repr(filtered_stack)) first 16 hex chars.

### Memory Benchmark Baseline (FR-132)
Baseline peak = maximum RSS during monolithic feature build under identical seed + data. Chunk peak measured with chunk mode enabled. Reduction = 1 - (chunk_peak / baseline_peak). Default target ≥ 0.25. Test fails if reduction < target unless env `MEM_REDUCTION_OVERRIDE=1` set (logs waiver reason).

### Observability Overhead Measurement (FR-154/155)
Two execution modes: instrumentation OFF (spans + timing collection disabled), ON (enabled). Overhead = (wall_time_on - wall_time_off) / wall_time_off. Must be < 0.03 (3%). If >= 0.03 and < 0.05 → warning; if ≥ 0.05 → failure (OBS_OVERHEAD_EXCEEDED).

### Distribution Determinism (FR-121)
Extending determinism rule: Increasing bootstrap trials only extends distribution; prefix hash of first min(old_trials, new_trials) samples must match. Decreasing trials truncates deterministically. Tested by comparing sha256 of ordered sample arrays.

---
Generated Addendum ensures all ambiguity items from analysis resolved prior to implementation.
