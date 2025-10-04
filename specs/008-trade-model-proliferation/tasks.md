# Tasks: Unified Trade & Equity Consistency Initiative

Feature: `008-trade-model-proliferation`
Spec: `specs/008-trade-model-proliferation/spec.md`
Plan: `specs/008-trade-model-proliferation/plan.md`

Legend:
- `[ ]` open / `[x]` done
- Priority: (P0 critical determinism / migration), (P1 core feature), (P2 polish)
- Parallelizable tasks marked with `[P]` (no shared primary file or DB migration sequencing conflict)
- Affects Hash: H (changes hashing outputs), NH (should not change), S (supports hashing infra only)
- Root: B=alphaforge-brain, M=alphaforge-mind, S=shared, Ops=scripts/infra

## Dependency Graph Overview
1. Baseline capture → 2. Canonical models & adapters → 3. Metrics & hashing consolidation → 4. Equity normalization → 5. Validation gating → 6. Optimization warning layer → 7. Migration tooling → 8. Cleanup & flag removal → 9. Docs & final verification

## Task List

### Phase 0 – Baseline & Research
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T001 | [x] | Inventory Trade/Equity Representations | Scan codebase for Trade/Equity/Position classes & emit table in `research.md`. | B | P0 | — | NH |
| T002 | [x] | Capture Baseline Determinism Hashes | Run 3 representative backtests; save JSON manifest `artifacts/baseline_hashes_v1.json`. | B | P0 | T001 | NH |
| T003 | [x] | Benchmark Runtime | 10k-bar runtime 5-run median; persist `artifacts/perf_baseline.json`. | B | P0 | T002 | NH |
| T004 | [x] | Metrics Key Inventory | List all existing metric keys & sources; append to research.md. | B | P1 | T001 | NH |
| T005 | [x] | Risk Register Draft | Enumerate risks (precision, migration, adoption) with mitigation in research.md. | B | P1 | T001 | NH |

### Phase 1 – Canonical Models & Contracts (Feature Flags OFF by default)
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T010 | [x] | Create Determinism Settings Module | Add `settings/determinism.py` with drawdown epsilon + env override. | B | P0 | T005 | NH |
| T011 | [x] | Define Fill Model | New `models/fill.py` Pydantic schema (atomic execution), doc FR refs. | B | P0 | T010 | NH |
| T012 | [x] | Define CompletedTrade Model | New `models/completed_trade.py` aggregated entry/exit trade. | B | P0 | T011 | NH |
| T013 | [x] | Review EquityBar Consistency | Align EquityBar docstring & ensure exposures+drawdown semantics unchanged. | B | P1 | T010 | NH |
| T014 | [x] | Draft Data Model Doc | Create `data-model.md` referencing canonical models & compatibility mapping. | B | P0 | T011,T012,T013 | NH |
| T015 | [x] | Add API Payload Extensions | Modify backtest response struct add `validation_caution`, `optimization_mode`, `advanced.warnings`. | B | P0 | T014 | NH |
| T016 | [x] | Feature Flags Scaffolding | Implement flag checks (`AF_UNIFIED_TRADES`, `AF_EQUITY_NORMALIZER_V2`). | B | P0 | T014 | NH |
| T017 | [x] | Compatibility Adapters | Adapter translating legacy internal structures to canonical & vice versa (temporary). | B | P0 | T016 | NH |
| T018 | [x] | Update Spec/Plan Cross-Refs | Link FR IDs to code comments (initial commit). | B | P2 | T014 | NH |
| T085 | [x] | Empty CompletedTrade Set Test | Test run with single fill / no round-trip yields empty CompletedTrade list & stable metrics. | B | P0 | T012,T017 | S |
| T090 | [x] | Drawdown Epsilon Override Test | Parametrized test validating epsilon impacts borderline drawdown only; no hash drift otherwise. | B | P0 | T010,T013 | S |
| T093 | [x] | Populate Contract JSON Schemas | Add concrete JSON examples (payload, Fill, CompletedTrade, warnings) under `contracts/`. | B | P1 | T015 | NH |
| T099 | [x] | Backtest Result Schema Snapshot Test | Snapshot test asserts presence of core keys & new T015 fields; guards against accidental removal. | B | P1 | T015 | NH |

### Phase 2 – Metrics & Hashing Consolidation
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T020 | [x] | Create Hashing Module | New `services/hashes.py` (metrics_signature, equity_signature). | B | P0 | T017 | S |
| T021 | [x] | Refactor metrics.calculator to Core | Move/merge into `services/metrics_core.py`; ensure identical outputs. | B | P0 | T020 | NH |
| T022 | [x] | Deprecation Shims | Add wrappers in old modules raising PendingDeprecationWarning. | B | P1 | T021 | NH |
| T023 | [x] | Hash Regression Tests | New tests verifying pre/post equivalence (except planned differences). | B | P0 | T020 | S |
| T024 | [x] | Update Equity Hash Callers | Replace legacy calls with consolidated hashing functions. | B | P0 | T020 | H |

### Phase 3 – Equity Normalization (Compare Mode)
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T030 | [x] | Implement Normalizer | `services/equity_normalizer.py` removing 1_000_000 scaling; provides dual-run output for diff. | B | P0 | T017 | H |
| T031 | [x] | Dual-Run Comparison Harness | Test that new equity track ~ old scaled semantics; thresholds documented. | B | P0 | T030 | S |
| T032 | [x] | Guard Flag Integration | Tie normalization behind `AF_EQUITY_NORMALIZER_V2`. | B | P0 | T030 | NH |
| T033 | [x] | Update Documentation | Quickstart section describing comparison workflow. | B | P1 | T031 | NH |
| T092 | [x] | Metrics Hash Stability Post-Normalization | Assert metrics_signature unchanged while equity_signature expected delta documented. | B | P0 | T031 | S |
| T034 | [x] | Normalizer Unit Test | Direct unit test for `normalize_equity` covering scaled vs already-normal & empty input. | B | P1 | T030 | NH |
| T035 | [x] | Preview Enrichment | Add `scaled`, `scale_factor`, `median_value` to `normalized_equity_preview` while retaining `median_nav`. | B | P2 | T032 | NH |
| T036 | [x] | Introduce AF_EQUITY_HASH_V2 Flag | Add flag gate & plumbing to optionally hash normalized equity sequence (no default behavior change). | B | P0 | T035 | S |
| T037 | [x] | Dual-Hash Comparison Test | Test recording legacy vs normalized equity hash under flag; asserts run hash still legacy. | B | P0 | T036 | S |
| T038 | [x] | Baseline Equity Hash Snapshot | Persist pre-switch equity hash manifest for documentation & future regression guard. | B | P1 | T037 | NH |
| T090A | [x] | Drawdown Epsilon Hash Invariance | Borderline epsilon drift test ensures metrics/equity hashes stable across epsilon widening. | B | P2 | T090 | NH |

### Phase 4 – Validation Caution Gating
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T040 | [x] | Compute Caution Flag | Extend validation runner to derive caution flag & triggering metrics. | B | P0 | T015,T023 | NH |
| T041 | [x] | Retention Policy Adjustment | Exclude flagged runs from promotion; documented and unit-tested (keep_full gating; pinned runs exempt). | B | P1 | T040 | NH |
| T042 | [x] | Backend Payload Update Tests | Contract tests verify new fields & semantics. | B | P0 | T040 | NH |
| T043 | [x] | Frontend Badge Rendering | Mind displays caution indicator & metric tooltips. | M | P1 | T042 | NH |
| T086 | [x] | Validation Disabled Behavior Test | Ensure caution flag false & list empty when validation disabled / distributions absent. | B | P0 | T040 | S |
| T097 | [ ] | Validation Persistence Test | DB row includes persisted caution_flag & triggering metrics artifact; verifies migration added column & backfill logic. | B | P0 | T040,T062 | NH |

### Phase 5 – Optimization Warning Layer
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T050 | [x] | Combination Enumerator | Compute param grid count & metadata; defer (no-exec) when > AF_OPTIMIZATION_MAX_COMBINATIONS. | B | P1 | T017 | NH |
| T051 | [x] | Structured Warning Emission | Populate `advanced.warnings` with `{ code: "OPTIMIZATION_DEFERRED", combinations, limit }`; set `optimization_mode="deferred"`. | B | P1 | T050 | NH |
| T052 | [x] | Frontend Warning Display | Show deferred optimization warning in UI (Results header alert) and support tooltip. | M | P2 | T051 | NH |
| T087 | [x] | Optimization Defer No-Exec Test | Verify `optimization_mode="deferred"` and warning emission when grid exceeds limit; baseline has no optimizer execution. | B | P0 | T051 | S |
| T088 | [ ] | Optimization Guard Error Contract Test | Large grid triggers deterministic error & warning fields validated. | B | P0 | T050 | S |

### Phase 6 – Migration Tooling
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T060 | [x] | Migration Script Skeleton | `scripts/migrations/unify_trades.py` dry-run (stdout + JSON). | Ops | P0 | T017 | NH |
| T061 | [x] | Idempotency Test | Ensure repeated migration no-ops second run. | B | P0 | T060 | NH |
| T062 | [x] | Backfill Validation Decision | Add caution_flag columns in runs_extras via migration; backfill from manifest. | B | P1 | T060 | NH |
| T063 | [x] | Manifest Version Injection | Add `trade_model_version` column in runs_extras and backfill from manifest. | B | P0 | T060 | NH |
| T064 | [ ] | Backward Compatibility Shim Removal Plan | Document final removal timeline for adapters in tasks or WAIVERS. | B | P2 | T060 | NH |
| T089 | [ ] | Trade Model Version Hash Exclusion Test | Assert run_hash unchanged when trade_model_version changes; version present in manifest. | B | P0 | T063,T023 | S |
| T091 | [ ] | Migration JSON Output Test | Validate JSON report path & schema produced by migration dry-run. | B | P0 | T060 | NH |
| T096 | [ ] | Migration Transform Correctness Test | Executes migration (non-dry) on fixture DB; verifies counts & field mappings for Fill vs CompletedTrade derivation. | B | P0 | T060 | NH |

### Phase 7 – Cleanup & Flag Removal
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T070 | [ ] | Remove Deprecated Shims | Delete legacy metric/trade adapter modules after parity confirmed. | B | P1 | T024,T061 | NH |
| T071 | [ ] | Remove Feature Flags | Hard-enable unified models & normalization after adoption threshold. | B | P1 | T070 | H |
| T072 | [ ] | Final Hash Snapshot | Capture post-cleanup hashes & compare to baseline (expected diffs documented). | B | P0 | T071 | S |
| T073 | [ ] | Documentation Final Pass | Update README, CHANGELOG, WAIVERS removal. | B | P1 | T071 | NH |
| T074 | [ ] | Constitution Compliance Re-check | Assert no new violations introduced. | Ops | P0 | T073 | NH |
| T095 | [ ] | Legacy Trade Artifact Sweep Test | Scan codebase ensures no residual legacy Trade/Position models exported publicly; fails if found. | B | P0 | T070 | NH |

### Phase 8 – Verification & Sign-off
| ID | Status | Title | Description | Root | Priority | Depends | Affects Hash |
|----|--------|-------|-------------|------|----------|---------|--------------|
| T080 | [ ] | Determinism Replay Suite | Multi-run repeat (5x) confirm stable hashes. | B | P0 | T072 | S |
| T081 | [ ] | Performance Regression Audit | Re-run benchmark; ensure <5% regression. | B | P0 | T072 | NH |
| T082 | [ ] | Retention Behavior Validation | Ensure caution runs not promoted; normal runs unaffected. | B | P1 | T041 | NH |
| T083 | [ ] | Frontend Contract Snapshot | Type generation & snapshot tests updated. | M | P1 | T073 | NH |
| T084 | [ ] | Final Sign-off Report | Produce acceptance summary referencing FRs & test evidence. | Ops | P0 | T080,T081,T082,T083 | NH |
| T094 | [ ] | Performance Early Alert Harness | Test harness asserts 3% alert triggers without failing final 5% gate. | B | P1 | T081 | NH |

### Parallel Execution Suggestions
- Group A (after T017): T020 [P], T021 [P] (separate modules), T023 [P]
- Group B (after T030): T031 [P], T032 [P], T033 [P]
- Group C (after T040 & T050): T041 [P], T042 [P], T051 [P]
- Group D (migration): T061 [P], T062 [P], T063 [P]

### Rollback Strategy
- Metrics consolidation: revert to legacy modules & disable feature flag
- Equity normalization: disable `AF_EQUITY_NORMALIZER_V2` and re-run baseline regression tests
- Caution gating: revert API additions & skip retention exclusion logic (flag guard)
- Migration: restore pre-migration DB backup and remove intermediate JSON report

### Open Risks Tracking (Linked Tasks)
- Precision drift in equity normalization (T031)
- Hidden legacy Trade references (T070)
- Hash parity anomalies (T023, T072, T080)
- Performance overhead from hashing consolidation (T081)

### Completion Criteria
All P0 tasks completed; determinism replay stable; performance target met; documentation & migration scripts validated; feature flags removed (or consciously retained with waiver).

---
Generated: 2025-10-01

## Next Phase Prep (Added 2025-10-01)

Upcoming Transitional Hashing (Phase 3.5 / early Phase 4):
- T036 introduces `AF_EQUITY_HASH_V2` (already declared in `settings/flags.py`). Implemented; dual-hash additive field `equity_curve_hash_v2` now appears only when both normalization & hash flags enabled.
- T037 dual-hash comparison: run once with flag off/on capturing `(legacy_equity_hash, normalized_equity_hash)` ensuring `metrics_hash` and `run_hash` unchanged. Store diff artifact `artifacts/equity_hash_transition.json`.
- T038 baseline snapshot: persist legacy equity hash manifest pre-switch (`artifacts/equity_hash_legacy_baseline.json`) referenced by README & CHANGELOG when switch occurs.

Design Notes:
- Equity hashing function will accept optional normalized series; if flag disabled, continue legacy path with identical serialization ordering & float formatting.
- Normalized path must round floats to <= 12 decimal places prior to hashing to reduce cross-platform FP jitter.
- Add regression asserting enabling flag does NOT alter ordering length or produce NaNs (sanity guard before making it default).

Validation Caution Schema Planning (Phase 4):
- New run payload fields: `validation_caution: bool`, `validation_caution_metrics: List[str]` (empty list when false / absent). Initially always `false` + empty list until T040.
- Add snapshot test (T042) expecting those fields only when flag or config threshold active (guard against premature emission).
- Retention gating (T041) will treat `validation_caution=True` as non-promotable; implement via existing retention filter chain.

Baseline Hash Documentation:
- Prior to turning on `AF_EQUITY_HASH_V2` in CI defaults, capture: `{ run_id, equity_hash_legacy, metrics_hash, created_at }` for 3 canonical configs to `artifacts/equity_hash_transition_baseline.json`.
- Update quickstart & README with a short table: Column(Phase, Flag, Equity Hash Source).

Risk Mitigations:
- If normalized hashing introduces drift: immediate rollback path by toggling flag off (no code revert required).
- Keep dual computation (legacy+normalized) for at least one release cycle to compare frequency distribution of hash collisions (should be none) & runtime overhead (<2%).
