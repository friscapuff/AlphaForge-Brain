# Tasks: AlphaForge Brain Refinement

**Feature Directory**: `specs/004-alphaforge-brain-refinement/`
**Spec**: `spec.md`
**Plan**: `plan.md`
**Research**: `research.md`
**Data Model**: `data-model.md`

Legend: `[P]` = Can execute in parallel (different files / no dependency); tasks execute top-to-bottom unless `[P]`.
Traceability: Each task lists covered FR IDs.

---
## Gate A: Architecture Migration (Must Complete Before Gate 0)
"Exit Criteria": No code remains under legacy `src/` or `tests/` (unless shim waiver documented), deterministic hash parity pre/post move, CI passing with integrity guard, constitution updated, status file PASS for each criterion.

### A1 Filesystem & Layout
- [x] T000 Establish dual-root skeleton: create `alphaforge-brain/`, `alphaforge-brain/src/`, `alphaforge-brain/tests/`, `alphaforge-mind/src/`, `alphaforge-mind/tests/`, `shared/`.
- [x] T001 Move existing backend code from `src/` → `alphaforge-brain/src/` preserving package (`alphaforge_brain`).
- [x] T002 Move tests from `tests/` → `alphaforge-brain/tests/` maintaining relative paths.
- [x] T002A Ensure test discovery: add `__init__.py` where required; verify `pytest -q` discovers equivalent count pre/post (store counts in status file).

### A2 Configuration & Tooling
- [x] T003 Update config files (`mypy.ini`, `pytest.ini`, `ruff.toml` or pyproject tool sections) to point to new roots; remove obsolete paths. (Completed: added explicit_package_bases to resolve duplicate module issue.)
- [x] T004 Add cross-root integrity script `scripts/ci/check_cross_root.py` (fail if brain imports mind or vice versa directly without waiver).
- [x] T005 Add `WAIVERS.md` template with waiver format & governance rules.

### A3 Determinism Baseline & Verification
- [x] T006 Implement baseline capture script `scripts/migration/capture_baseline.py` producing `zz_artifacts/migration_baseline.json` (hash of key artifacts, run hash, file digest map).
- [x] T006B Execute baseline capture BEFORE any moves; commit artifact (pointer) (mark timestamp in status file).
- [x] T007 Implement post-move verification script `scripts/migration/verify_post_move.py` (re-run deterministic pipeline, produce comparison report `zz_artifacts/migration_verification.json`).
- [x] T007B Execute post-move verification; assert parity (strict equality for run hash + all tracked digests, allow configurable ignore list for timestamps/meta). (Result: run_hash parity OK; expected config files changed: `mypy.ini`, `pytest.ini`, `pyproject.toml`.)

### A4 Documentation & Governance
- [x] T008 README update: reflect dual-root, add brief migration rationale & diagram note (link to architecture diagram placeholder).
- [x] T009 Remove legacy `src/` and `tests/` directories (if not needed for shim) OR add shim with explicit removal date in `WAIVERS.md`. (Legacy dirs removed; no shim required.)
- [ ] T009A If shim used: create `shim/README.md` describing purpose, removal deadline, files enumerated.
- [x] T010 Governance record: append Architecture Migration completion note in `constitution.md` (include hash of status file).

### A5 CI Integration & Finalization
- [x] T011 CI pipeline update to run integrity script + updated test paths + baseline verification step (optional nightly parity re-run).
- [x] T012 Record exit criteria status file `alphaforge-brain/ARCH_MIGRATION_STATUS.md` listing each criterion PASS/FAIL with evidence hashes.
- [x] T013 Add migration retrospective `ARCH_MIGRATION_RETROSPECTIVE.md` (risks found, mitigations, delta time, recommendations for future structure changes).
- [x] T014 Tag repository (e.g., `migration-complete-v1`) & update CHANGELOG entry summarizing architectural change.
- [x] T015 Remove any temporary waivers related purely to migration (clean `WAIVERS.md`).

---
## Gate 0: Planning Completion
- [x] T090 Confirm final FR set & document any late clarifications (none currently). (Meta)
	- See: `specs/004-alphaforge-brain-refinement/spec.md` Clarifications & Addendum (no open NEEDS CLARIFICATION).
- [x] T091 Draft JSON Schema for extended manifest (FR-141).
	- Added: `specs/004-alphaforge-brain-refinement/contracts/manifest.schema.json` (draft-07).
- [x] T092 Migration framework scaffold + initial V1 script (FR-100).
	- Added doc: `specs/004-alphaforge-brain-refinement/migration-framework.md` (loader, naming, verification).
- [x] T093 Regression hash test plan (chunking + replay) documented (FR-130, FR-131, FR-142).
	- Added: `specs/004-alphaforge-brain-refinement/regression-test-plan.md` (golden hash rules).
- [x] T094 CI job outline (determinism replay, bootstrap width gate) approved (FR-151, FR-152, FR-150).
	- Added: `specs/004-alphaforge-brain-refinement/ci-outline.md` (jobs, gates, provenance echo).

---
## Phase A: Persistence & Schema (FR-100–105, FR-140–142, FR-150)
- [x] T100 Create SQLite schema & migration bootstrap `src/infra/persistence.py` (FR-100, FR-140).
	- Done: Dynamic migration runner in `alphaforge-brain/src/infra/db.py`; core schema in `infra/migrations/002_core_schema.sql`; baseline `001_init.sql` trimmed.
- [x] T101 Add manifest persistence + run insert logic (FR-101, FR-103, FR-140).
	- Done: `infra/persistence.py:init_run()` persists config/manifest + status/seed/db_version.
 - [x] T102 Add equity/trades bulk insert transaction at finalize (FR-102).
	 - Done: `infra/persistence.py:finalize_run()` inserts trades+equity in one transaction and returns row counts; covered by `tests/infra/test_finalize_run.py`.
 - [x] T103 Add metrics persistence helper (FR-105) and record row counts (FR-105).
	 - Done: Row-count metrics auto-recorded in `finalize_run` (keys: `rows_trades`, `rows_equity` with `phase="finalize"`).
- [x] T104 Add validation persistence writer (FR-121, FR-124).
	- Done: `insert_validation` with method/block_length/jitter/fallback fields.
 - [x] T105 Add feature cache metadata table + manifest linkage (FR-100, FR-103).
	 - Done: `infra/persistence.py:record_feature_cache_artifact()` computes parquet digest/shape, upserts `features_cache`, and appends entry to `runs.manifest_json`; covered by `tests/infra/test_feature_cache_meta.py`.
 - [x] T106 Implement read/query helpers by run_hash returning typed objects (FR-104).
	 - Done: Added `RunRow` dataclass + `get_run_typed()` (minimal typed accessor for runs). Additional typed readers can be added later as needed.
- [x] T107 JSON schema validation hook for manifest (FR-141).
	- Done: `validate_manifest_object` stub; uses jsonschema when available.
 - [x] T108 Round-trip replay test including SQLite → artifact reconstruction (FR-142).
	 - Done: Extended `tests/integration/test_persistence_roundtrip.py` to re-materialize trades/equity from DB and compare canonical content hashes to original rows.
- [x] T109 Migration verification script + expected head checksum (FR-150).
	- Done: `scripts/ci/verify_migrations_head.py`, `scripts/ci/check_migrations_head.py`, and `MIGRATIONS_HEAD.txt` (HEAD=002_core_schema).

---
## Phase B: Causality & Determinism (FR-110–113, FR-151, FR-156)
- [x] T110 Implement `CausalAccessContext` STRICT/PERMISSIVE (FR-110, FR-113).
- [x] T111 t→t+1 fill invariant tests & enforcement (FR-112).
	Evidence: `tests/execution/test_simulator.py::test_t_plus_one_fill_rule` and integration tests ensure fills occur at t+1.
- [x] T112 Feature/indicator shift enforcement test (FR-112).
	Added: `tests/unit/test_feature_shift_enforcement.py`.
- [x] T113 Surface guard stats + mode in metrics & manifest (FR-111, FR-113).
	Added helper `infra.persistence.record_causality_stats` + `tests/infra/test_causality_persistence.py`.
- [x] T114 Deterministic seed derivation helper (FR-151 support).
	Added: `src/infra/utils/seed.py` with `derive_seed`; covered by unit/integration tests.
- [x] T115 Two-run determinism replay test harness (FR-151).
	Added: `tests/integration/test_determinism_replay.py`.
- [x] T116 Guard overhead benchmark (ISSUE-CAUSAL-001) (<1% overhead target) (Risk Mitigation).
	Added: `scripts/bench/causality_guard_overhead.py`.

---
## Phase C: Statistical Breadth (FR-120–124, FR-152)
- [x] T120 HADJ-BB block length heuristic implementation + docstring formula (FR-120).
- [x] T121 Bootstrap engine with fallback simple IID (FR-120, FR-121, FR-124).
- [x] T122 Integrate bootstrap results into validation & metrics artifacts (FR-121, FR-124).
- [x] T123 Walk-forward robustness aggregator (FR-123). (Added aggregate summary fields in validation runner.)
- [x] T124 CI width gate logic + policy (ANY metric width > threshold triggers failure) (FR-122, FR-152). (Added script scripts/ci/bootstrap_ci_width_gate.py and test.)
- [x] T125 Fallback scenario integration test (FR-120, FR-124). (tests/validation/test_hadj_bb.py covers IID and short series fallback.)
- [x] T126 Deterministic distribution reproducibility test (FR-121). (tests/validation/test_hadj_bb.py ensures deterministic distribution for fixed seed.)

---
## Phase D: Data Pipeline & Memory (FR-130–132)
- [x] T130 Implement deterministic chunk iterator (FR-130).
- [x] T131 Refactor feature builder to optional chunk mode (FR-131).
- [x] T132 Multi-window overlap policy & tests (FR-130) (Clarification Addendum).
- [x] T133 Memory benchmark harness & target assertion (baseline vs chunk) (FR-132).
- [x] T134 Feature cache determinism test (FR-131).

---
## Phase E: Artifact & Provenance Enhancements (FR-103, FR-140–142, FR-154–158)
- [x] T140 Add provenance fields (db_version, bootstrap_seed, walk_forward_spec) (FR-103, FR-140).
	- Done: `infra.persistence.init_run` already persisted `db_version`, `bootstrap_seed`, and optional `walk_forward_spec` into `runs` row; `RunRow` typed reader includes these fields.
- [x] T141 Add canonical JSON writer + content hash persistence (FR-140).
	- Done: `init_run` uses `canonical_json` for config/manifest and persists `config_json_hash` and `manifest_json_hash` metrics (sha256) at phase="init".
- [x] T142 JSON schema validation already added (see T107) – cross-verify (FR-141).
	- Done: `validate_manifest_object` present; no changes required; cross-verified wiring remains intact.
- [x] T143 Replay test already (see T108) – finalize & extend for features cache (FR-142).
	- Done: Existing roundtrip test verifies content hashes; features cache determinism covered in Phase D integration tests.
- [x] T144 Phase timing instrumentation (FR-154).
	- Done: Added `record_phase_timing` writing to `phase_metrics` with duration and optional rows/extra JSON.
- [x] T145 Lightweight tracing spans instrumentation (distinct from timing) (FR-155).
	- Done: Added `record_trace_span` convenience which writes a timing row with span name and attributes.
- [x] T146 Run error logging persistence (FR-156).
	- Done: Added `record_run_error` inserting into `run_errors`.
- [x] T147 Phase completion markers persistence (FR-157).
	- Done: Added `record_phase_marker` that writes a zero-duration marker in `phase_metrics` and updates `manifest_json.phase_markers`.
- [x] T148 Minimal credential provider stub (FR-158).
	- Done: Added `infra/credentials.py` with `get_env_credential` (env-based, no persistence).
- [x] T149 Observability overhead benchmark (<3% wall-clock) (FR-154, FR-155 Success Metric).
	- Done: Added `alphaforge-brain/scripts/bench/observability_overhead.py` measuring median runtime off vs on and asserting overhead < threshold.

---
## Phase F: CI & Tooling (FR-150–152, FR-151 reuse)
- [x] T150 Determinism replay CI script (FR-151).
	- Added: `alphaforge-brain/scripts/ci/determinism_replay.py`; CI job `determinism-replay` runs it and uploads `zz_artifacts/determinism_replay.json`.
- [x] T151 Bootstrap CI width gate script (FR-152, FR-122).
	- Added earlier under Phase C as `alphaforge-brain/scripts/ci/bootstrap_ci_width_gate.py`; wired into CI in build-test and acceptance suite.
- [x] T152 Schema dump artifact generator (FR-153).
	- Added: `alphaforge-brain/scripts/ci/dump_schema.py`; CI dumps to `zz_artifacts/schema.sql` and uploads artifact `sqlite-schema`.
- [x] T153 Integrate migration verification in CI (FR-150).
	- CI step `Verify migrations HEAD checksum` runs `scripts/ci/check_migrations_head.py`; nightly `migration-parity` retains allow-fail parity check.
- [x] T154 Final acceptance suite orchestrator (aggregates determinism, bootstrap, replay) (Multiple FRs summary).
	- Added: `alphaforge-brain/scripts/ci/acceptance_suite.py`; CI job `acceptance-suite` runs it and uploads `zz_artifacts/acceptance_summary.json`.

---
## Phase G: Documentation (FR-160–162 + Clarity Addendum)
- [x] T160 Contracts appendix (schemas, fields, error_code taxonomy) (FR-160, FR-156 clarification).
	- Added: `specs/004-alphaforge-brain-refinement/contracts-appendix.md` (plain-language coverage of manifest schema, persistence entities, validation artifacts, error codes, OpenAPI, determinism).
- [x] T161 Persistence quickstart (run → query) (FR-161).
	- Added: `specs/004-alphaforge-brain-refinement/persistence-quickstart.md` (step-by-step, non-technical guide from starting a run to viewing results in SQLite).
- [x] T162 README update (persistence, bootstrap, walk-forward, chunk mode) (FR-162).
	- Updated: `README.md` with sections and links to the above docs.
- [x] T163 Architecture diagram (supports FR-160 narrative).
	- Added: `specs/004-alphaforge-brain-refinement/architecture-diagram.md` (Mermaid diagram with plain-language narrative).
- [x] T164 Add HADJ-BB heuristic & CI width policy addendum section (FR-120, FR-122 clarity).
	- Added: `specs/004-alphaforge-brain-refinement/hadj-bb-ci-width-policy.md` (plain-language explanation of heuristic and CI width gate).

---
## Phase H: Validation & Sign-Off
- [x] T170 Validation checklist execution (map each FR to test evidence).
	- Added: `specs/004-alphaforge-brain-refinement/validation-checklist.md` (plain-language mapping of FRs to tests and CI artifacts).
- [x] T171 ACCEPTANCE.md compilation (targets vs observed metrics) (All FRs).
	- Added: `specs/004-alphaforge-brain-refinement/ACCEPTANCE.md` (summary of targets vs observed, evidence index, sign-off recommendation).
- [x] T172 Final governance review vs constitution (All FRs once constitution populated).
	- Updated: `.specify/memory/constitution.md` Governance Record with Phase H sign-off entry and references to acceptance artifacts.

---
## Added / Clarified Policies (Referenced by tasks)
- CI Width Gate: Fail if ANY monitored metric CI width exceeds threshold in STRICT mode; warn otherwise.
- HADJ-BB Block Length Heuristic (initial): 1) Compute lag-1..L (L=50 cap or N/4, whichever smaller) ACF; 2) Select smallest lag k where ACF(k) < τ (τ=0.1) after first local minimum; if none, use cap L; jitter +/-1 with deterministic seed; fallback to IID if N < 5k or mean(|ACF(1..k)|) < 0.05.
- Multi-window Chunk Overlap: Overlap size = max(required_window_sizes)-1; all rolling windows computed within chunk use internal shift to avoid forward leakage; last chunk tail extended via last overlap only.
- Memory Benchmark Baseline: Baseline = monolithic build peak RSS on identical input; reduction = 1 - (chunk_peak / monolithic_peak); target >= configured threshold (default 25%).
- Observability Overhead: Compare runtime with instrumentation toggled off vs on (same seed/dataset); overhead = (on - off)/off.
- Error Code Taxonomy (initial): PERSIST_xxx, CAUSAL_xxx, STATS_xxx, PIPE_xxx, OBS_xxx, CI_xxx (codes enumerated in appendix).

---
## Appendix: What changed (2025-09-24)
New/modified files for Phase B:
- src/services/causality_guard.py: CausalAccessContext alias/context; STRICT/PERMISSIVE.
- src/infra/utils/seed.py and src/infra/utils/__init__.py: derive_seed helper.
- src/services/__init__.py: package init for services.
- tests/unit/test_causality_and_seed.py: unit tests for guard and seed.
- tests/unit/test_feature_shift_enforcement.py: shift enforcement test.
- tests/infra/test_causality_persistence.py: persistence of causality stats.
- tests/integration/test_determinism_replay.py: two-run determinism harness.
- scripts/bench/causality_guard_overhead.py: micro-benchmark script.
New/modified files for Phase D:
- src/services/chunking.py: iter_chunk_slices + compute_required_overlap.
- src/domain/features/engine.py: build_features_chunked and public build_features chunk wiring.
- tests/unit/test_chunking.py: chunk slices and chunked equals monolithic tests.
- tests/integration/test_feature_cache_determinism_chunk.py: cache determinism with chunking.
- scripts/bench/feature_chunk_memory.py: memory reduction benchmark harness.

Added
- `alphaforge-brain/tests/infra/test_finalize_run.py` — unit test: finalize_run inserts trades/equity in one transaction and records row-count metrics.
- `alphaforge-brain/tests/infra/test_feature_cache_meta.py` — unit test: record_feature_cache_artifact upserts features_cache and updates runs.manifest_json.

Modified
- `alphaforge-brain/src/infra/persistence.py` — added `record_feature_cache_artifact` helper; wired up optional parquet shape read; exported symbol; minor imports.
- `alphaforge-brain/tests/integration/test_persistence_roundtrip.py` — extended to re-materialize trades/equity from DB and compare canonical content hashes to original rows.

## Validation Checklist (Auto-Derived)
- Persistence (FR-100–105): T100–T108 complete
- Causality (FR-110–113): T110–T115 + T116 benchmark
- Statistics (FR-120–124): T120–T126
- Pipeline (FR-130–132): T130–T134
- Integrity & Provenance (FR-140–142): T140–T143
- CI/Obs (FR-150–158): T144–T149, T150–T153
- Documentation (FR-160–162): T160–T164

---
Generated 2025-09-23 (Deduplicated / Gate A Expanded).

---
## Housekeeping Updates (2025-09-24)
- [x] Remove root archive `Alphaforge Brain.zip` (not needed; reduces root clutter).
- [x] Silence pytest-asyncio deprecation by pinning defaults in `pytest.ini` (`asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=function`).
- [x] Document local-only artifacts and non-commit policy in README/TESTING.
- [x] Move DB migration SQL to package: `infra/migrations/001_init.sql` → `alphaforge-brain/src/infra/migrations/001_init.sql`; add `importlib.resources` loader and update `infra/db.py` to use it.
- [x] Remove duplicate root `infra/` directory to avoid module ambiguity.
- [x] Clarify dataset location policy: prefer root `./data/NVDA_5y.csv`; packaged dataset is for fallback only and may be removed later.
- [x] Add CI guard to fail if generated artifacts are tracked: added step in `.github/workflows/ci.yml` to block files like `coverage.xml`, `typing_timing.json/md`, `mypy_*`, `diff_test.md`, `virt_report.json`, and `base-*.yaml`/`head-*.json`.
- [x] Add pre-commit cleanup and guard: `scripts/cleanup/remove_generated_artifacts.py` auto-removes local artifacts; `.pre-commit-config.yaml` blocks staging these files.
- [x] Update ARCH_MIGRATION_STATUS.md commit to tag commit `migration-complete-v1`.
- [x] Add CI step to echo SHA-256 of `alphaforge-brain/ARCH_MIGRATION_STATUS.md` for build log traceability.
- [x] Fix `poetry.lock` hash check by adding `scripts/env/poetry.lock.sha256` (env-check now passes the checksum stage).

Notes:
- CI continues to upload coverage/timing artifacts; they are ignored locally.
- Further root artifacts, if any, should be placed under `zz_artifacts/`.

---
## Type Hygiene Sweep (Pre-Gate 0 Enablement)
Objective: Reduce current mypy error count (baseline 11 across 7 files) to zero under existing strict settings, then stage and adopt an elevated lint + type regime ("strict-plus") before commencing Gate 0 implementation tasks. This ensures new Phase work begins on a fully typed, style-consistent foundation.

### Baseline Snapshot
- Source: `zz_artifacts/type_hygiene/mypy_baseline_raw.txt` (captured 2025-09-23 UTC)
- Structured: `zz_artifacts/type_hygiene/mypy_baseline.json`
- Grouped Markdown: (to be generated) `zz_artifacts/type_hygiene/mypy_grouping.md`
- Summary: 11 errors / 7 files / codes: assignment(2), call-arg(2), redundant-cast(3), return-value(1), type-arg(1), misc(1), no-any-return(1)

### Error Grouping → Planned Fix Batches
1. Redundant casts (`redundant-cast`, 3) – low risk cleanup.
2. Keyword argument mismatches (`call-arg`, 2) – likely signature drift or incorrect forwarding.
3. Assignment type mismatches (`assignment`, 2) – refine variable annotations or upstream types.
4. Return type mismatch (`return-value`, 1) – unify metadata type alias vs concrete.
5. Generic parameter omission (`type-arg`, 1) – add concrete dict key/value types.
6. Conditional signature mismatch (`misc`, 1) – align overload / conditional definitions.
7. Any-return elimination (`no-any-return`, 1) – tighten factory/registry return typing.

### Strict Upgrade Plan (Staged)
Stage 0 (Now): Maintain current `strict = true` (already many disallow_any flags on). Baseline & fix.
Stage 1 (Allow-Fail in CI): Introduce enhanced mypy config overlay:
	- `disallow_incomplete_defs = True`
	- `no_implicit_reexport = True`
	- `warn_unreachable = True`
	- `warn_unused_ignores = True` (already active)
	- `strict_equality = True`
	- Evaluate turning off `ignore_missing_imports` for first-party + selected third-party pinned libs (create per-module explicit stubs list).
Stage 2 (Promotion): Merge overlay into primary `mypy.ini`, remove waivers.

Ruff Strict Enhancements (Overlay then Promote):
	- Expand `select` with: "ANN", "D", "SLOT", "ASYNC", "DTZ" (if applicable), "TRY", "TCH".
	- Consider enabling complexity signals: `C90` (cyclomatic) with threshold policy doc.
	- Add docstring minimal completeness for public domain modules (ANN depends on clarity; ensure not overburdening internal helpers initially).
	- Introduce per-file ignores only when justified with inline comment referencing task ID.

### Artifacts & Metrics
- Trend file: `zz_artifacts/type_hygiene/metrics_history.json` (append {timestamp, total_errors, by_code, noqa_counts, ruff_violations} per run)
- Status markdown: `TYPE_HYGIENE_STATUS.md` (living summary; embed latest snapshot hash).
- Governance note: Add section to `constitution.md` after adoption describing enforced gates.

### Tasks (TH-series)
- [x] TH00 Generate grouped markdown (`mypy_grouping.md`) & initial `metrics_history.json` entry.
- [x] TH01 Fix redundant casts.
- [x] TH02 Resolve `call-arg` keyword mismatches.
- [x] TH03 Resolve assignment mismatches.
- [x] TH04 Fix return-value mismatch.
- [x] TH05 Add missing generic type parameters.
- [x] TH06 Align conditional function signatures (`misc`).
- [x] TH07 Eliminate Any-return case.
- [x] TH08 Verify zero errors (baseline strict) & record metrics history snapshot.
- [x] TH09 Draft mypy strict-plus overlay (`mypy.strictplus.ini`). (Completed: file present at repo root.)
- [x] TH10 Draft ruff strict overlay (`ruff.strictplus.toml` or pyproject section variant) & allow-fail CI job. (Overlay file created; CI wiring pending under TH11.)
- [x] TH11 CI integration (dual pass: baseline required, strict-plus allow-fail + metrics append).
- [x] TH12 Address new findings under strict-plus until clean; update overlays incrementally.
- [x] TH13 Promote overlays → primary configs; remove obsolete excludes (`exclude = ["src", "tests"]` in ruff once fully migrated).
- [x] TH14 Update `CHANGELOG.md` (Type Hygiene Sweep completion) & add governance note.
- [x] TH15 Gate 0 readiness assertion: zero errors baseline + strict-plus fully enforced.
- [x] TH16 Max Type Hinting Consolidation: coverage script implemented, functions 100%, methods 100%, class attrs 95.75% (≥95% target), constants excluded per Profile B.

Exit Criteria (Sweep):
1. `mypy` (baseline config) → 0 errors.
2. `mypy` (strict-plus overlay) → 0 errors pre-promotion.
3. `ruff` strict overlay → 0 new critical violations (document any accepted waivers with rationale).
4. Metrics trend demonstrates monotonic non-increasing error counts (no regressions accepted).
5. CI pipeline enforces baseline; strict-plus promoted within sweep window before Gate 0 feature work begins.
6. Max Type Hinting: 100% annotation coverage of public API (modules under `domain`, `services`, `api`, `infra`) with enforcement script.

Notes:
- Overlay approach isolates risk; revert path is single commit reversion.
- Any non-trivial stub additions documented with upstream issue reference if third-party packages lack types.
- Waivers in `WAIVERS.md` must include deprecation date ≤ 30 days from introduction.

Governance (Promotion Placeholder):
- Upon TH13–TH15 execution, append a Constitution amendment summarizing: (a) adoption of strict-plus flags merged into primary configs; (b) ratchet policy (no increase in error_count, function/method/class_attr coverage); (c) waiver lifecycle (30-day expiry) and enforcement script reference (`scripts/type_hygiene/ci_append_metrics.py`).
- Add CHANGELOG entry: "Type Hygiene Sweep Complete: baseline + strict-plus promoted, zero mypy errors, coverage gates active (Profile B)." Reference metrics history hash of final pre-promotion snapshot.

### Selected Policy Profile: B (Balanced Progressive)
Adopted 2025-09-23. Rationale: Maximizes signal (functions/methods) with manageable churn; defers noisy constant annotations.

Policy Parameters:
- Functions: 100% full param + return annotations (enforced now).
- Methods: 100% (currently ~95%; TH16 subtasks will close gap).
- Class Attributes: ≥95% (public, non-underscore) — will ratchet higher post Gate 0 if value demonstrated.
- Module Constants: Temporarily excluded (MC-NONE). Re-evaluate after Gate 0; track count but do not gate.
- Implicit Any: Disallowed via existing disallow_any* flags (maintain); boundary Any requires timeboxed waiver.
- ignore_missing_imports: STAGED removal — prepare stubs / targeted ignores; drop global flag after mypy baseline = 0 and method coverage = 100%.
- CI Gates: Dual (baseline required + strict-plus allow-fail) + ratchet (no coverage regression for functions/methods/class attrs metrics).
- Waivers: Must include `expires_at` ≤ 30 days + issue link.

Implementation Actions (Profile B):
1. Enhance coverage script to ignore constants for gating while still reporting counts.
2. Add ratchet logic (future TH16 step) comparing previous JSON snapshot.
3. Annotate remaining methods to reach 100%.
4. Annotate minimal class attrs to reach ≥95% (then lock).
5. Remove `ignore_missing_imports` after stubs pass.
6. Reconsider constants threshold post Gate 0 (add decision entry in governance).

Coverage Snapshot (2025-09-23): functions=100%, methods=100%, class_attrs=95.75%, constants=29.79% (excluded from gating).
