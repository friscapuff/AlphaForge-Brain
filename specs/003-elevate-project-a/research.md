# Phase 0 Research: Truthful Run Foundation

## Decisions Summary
| Topic | Decision | Rationale | Alternatives | Future Considerations |
|-------|----------|-----------|-------------|-----------------------|
| Causality Guard | Runtime strict `CausalContext` + proxy accessors | Immediate enforcement, low complexity, zero-copy windows | AST static analysis (brittle), monkeypatch global df (fragile), copying slices (perf) | Potential hybrid static pre-check if strategies grow complex |
| Float Determinism | precision=8 fixed, np/pandas global settings (FR-041) | Stable hashing, human-readable, sufficient for PnL accuracy | Higher precision (noise in hashes), decimal module (perf overhead) | Revisit for intraday microstructure if rounding error matters |
| API Versioning | Phase 1 = package version only | Simplicity, aligns with Principle 9 | Custom header early (unneeded), URL versioning (inflexible) | Phase 2 preview header, Phase 3 media-type if breaking change |
| Permutation Parallelism | Precomputed seed list + order sort | Deterministic, simple merge | Joblib dynamic RNG (ordering risk), single-thread loop (slow) | Scale-out via thread/process pool with same seed scheme |
| Borrow Cost Accrual | Linear per-bar accrual | Transparent, easy to audit | Continuous compounding (complex), end-of-period lump sum (less faithful) | Multi-rate borrow tiers, intraday scaling |
| Run Config Hashing | Canonical JSON (sorted keys) | Human diffable, stable ordering | Pickle (not stable), msgpack (less readable) | Protobuf schema if multi-language clients needed |

| Walk-Forward Segmentation | Rolling train/test windows (fixed or sliding) (FR-046, FR-048) | Direct temporal robustness read; mirrors production retrain cadence | K-fold time permutation (less interpretable), single holdout only (narrow) | Adaptive dynamic window sizing (FR-049 future) |
| Robustness Reporting | Composite of p-value + OOS stability + tail stats (FR-047) | Multi-axis view reduces over-reliance on single metric | Raw p-value only (myopic), multiple corrections prematurely (complex) | Expand to include effect size confidence bands |
| Bias-Preventive Splits | Enforced chronological non-overlap with optional warm-up (FR-048) | Eliminates leakage, reproducible segments | User-managed manual indices (error-prone) | Auto regime detection for boundary placement |

## Detailed Rationale
### 1. Causality Guard
Proxy restricts index range; O(1) violation detection. Static approaches defer due to complexity and dynamic strategy code potential.

### 2. Float Determinism
Precision 8 balances stability vs fidelity; financial metrics with daily bars unaffected beyond 1e-6 tolerance. Manifest records policy, facilitating future adjustment with explicit version note.

### 3. API Versioning
Avoids premature negotiation surfaces; additive changes safe. ISSUE-API-VERS-001 tracks trigger conditions.

### 4. Permutation Parallelism
Seeds = base_seed + i ensures reproducibility independent of execution order. Sorting distribution by index yields stable artifact hash.

### 5. Borrow Cost Accrual
Chosen formula matches intuitive daily cost drag; clearly attributable in ledger; enables component-level PnL analysis.

### 6. Run Config Hashing
Stable JSON prevents environment-specific ordering differences; hashing excludes volatile fields (timestamps) except canonical created_at which is stored but not hashed.

### 7. Walk-Forward Segmentation (FR-046, FR-048)
Chosen over static holdout because it surfaces stability across temporal regimes. Fixed-size sliding window simpler, deterministic. Parameter optimization confined to in-sample segment ensures isolation; out-of-sample metrics recorded separately. Segments serialized (train_start, train_end, test_start, test_end) for audit.

### 8. Robustness & Hypothesis Reporting (FR-047)
Single p-value risks false confidence. Design integrates: permutation p_value, extreme_tail_ratio (tail emphasis), oos_consistency_score (dispersion of OOS returns/Sharpe), proportion_of_profitable_oos_segments. Composite robustness_score = weighted normalized components (weights documented). Deterministic rounding prior to hashing.

### 9. Bias-Preventive Temporal Splits (FR-048)
Mandated chronological ordering prevents feature leakage from train/test overlap. Optional warm-up window excluded from metrics but allows indicator initialization. Validation rejects overlapping or reversed intervals.

### 10. Future Adaptive / Meta Validation (FR-049 - Future)
Deferred to avoid speculative complexity. Potential directions: regime change detection triggering dynamic re-windowing; meta-evaluation across multiple strategies adjusting significance thresholds (multiple testing control). Will require additional statistical governance before promotion.

## Open (Tracked) Issues
- ISSUE-GUARD-001 (implementation) — design settled, performance measurement pending.
- ISSUE-CANCEL-001 (defer) — revisit post orchestrator enhancements.
- ISSUE-API-VERS-001 (monitor) — no immediate action.
- ISSUE-VAL-WF-001 (walk-forward implementation) — in-scope.
- ISSUE-VAL-ROB-001 (robustness reporting) — in-scope.
- ISSUE-VAL-SPLIT-001 (split enforcement) — in-scope.
- ISSUE-VAL-ADAPT-001 (adaptive/meta validation) — future.

## No Remaining Clarifications
All prior NEEDS CLARIFICATION items resolved or deferred with issues.

## Ready for Phase 1
Research gate passed; proceed to design & contracts artifacts.

## Phase 1 Promotion Delta
Walk-forward & robustness elevated to MUST after user mandate (post initial research). This addendum preserves original decisions while expanding validation architecture.
