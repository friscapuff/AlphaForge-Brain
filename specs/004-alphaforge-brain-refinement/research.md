# Phase 0 Research: AlphaForge Brain Refinement

**Branch**: 004-alphaforge-brain-refinement
**Spec**: ./spec.md
**Plan**: ./plan.md
**Status**: Draft (In-Progress Phase 0)

---
## Objectives
Establish empirical + analytical grounding for adaptive bootstrap design, memory & performance improvements, feature cache keying, and chunked pipeline correctness before implementation.

## Research Tracks & Placeholders
| ID | Track | Purpose | Key Questions | Artifacts | Exit Criterion |
|----|-------|---------|---------------|-----------|----------------|
| R1 | Block Length Heuristic | Validate capped adaptive block length selection | Does capped heuristic (<=50) retain ACF structure for typical symbol? | ACF plots, summary table | Selected formula justified & documented |
| R2 | Float32 Precision Impact | Quantify metric drift vs float64 | Sharpe/CAGR delta < 1e-4 relative? Any instability? | Comparison metrics table | Thresholds documented & accepted |
| R3 | Numba Kernel ROI | Assess speedups & compile overhead | SMA/volatility/drawdown speedup factor? JIT warmup cost? | Timing benchmarks | Proceed / fallback decision recorded |
| R4 | Parquet IO Profile | Compare pyarrow selective read vs CSV baseline | Memory footprint & time improvement? | Timing & memory logs | Adoption rationale captured |
| R5 | SQLite Bulk Insert Strategy | Find optimal insert mode | WAL + batch size sweet spot? | Rows/sec table | Chosen mode + batch size fixed |
| R6 | Feature Cache Key Stability | Ensure deterministic canonical key string | Are param orderings stable? Hash collisions risk? | Hash derivation examples | Canonical key spec written |
| R7 | Chunk Overlap Correctness | Verify rolling window continuity across chunks | Any boundary discontinuities? | Boundary diff report | Overlap approach validated |
| R8 | Bootstrap Runtime Scaling | Trials runtime vs dataset length | Runtime linearity within tolerance? | Scaling plot | Complexity assumptions validated |
| R9 | Seed Derivation Determinism | End-to-end reproducibility | Any nondeterministic drift across runs? | Hash comparison log | Reproducibility confirmed |

---
## Methodology Snippets (To Fill)
### R1 Block Length Heuristic
- Data Sources: Synthetic AR(1), Real sample (choose stable equity minute bars subset)
- Steps: compute ACF → detect first lag < 1/e → apply heuristic → compare variance retention vs simple IID

### R2 Float32 Precision Impact
- Compute metrics (Sharpe, CAGR, max_drawdown) on float64 canonical; downcast; recompute; relative error table.

### R3 Numba Kernel ROI
- Kernels: SMA (window 20, 50, 200), rolling volatility, drawdown path.
- Collect: warm vs hot execution times, speedup factors.

### R4 Parquet IO Profile
- Compare: pandas.read_csv vs pyarrow.parquet read selected columns (timestamp, close) vs all columns.

### R5 SQLite Bulk Insert Strategy
- Experiment: batch sizes (1k, 5k, 10k, 50k), WAL on/off, synchronous=NORMAL.

### R6 Feature Cache Key Stability
- Canonical key: sha256(json.dumps({dataset_hash, indicator, version, params_sorted, seed_root, code_version}, sort_keys=True)).

### R7 Chunk Overlap Correctness
- Validate no NaN seams: compare rolling window outputs contiguous vs chunked for multiple window sizes.

### R8 Bootstrap Runtime Scaling
- Trials: 100, 200, 500, 1000 at fixed dataset; measure per-metric distribution time; evaluate slope.

### R9 Seed Derivation Determinism
- Run identical config twice; diff all run-relevant hashes (DB rows, artifact digests, bootstrap distributions).

---
## Benchmark Data Template (Populate)
| Track | Case | Metric | Value | Notes |
|-------|------|--------|-------|-------|
| R1 | AR1 phi=0.4 | block_len | TBD |  |
| R2 | baseline | sharpe_rel_err | TBD |  |
| R3 | SMA-50 | speedup | TBD | hot loop |
| R4 | parquet selective | mb_savings | TBD |  |
| R5 | batch=10k WAL | rows_per_sec | TBD |  |
| R6 | example key | length | TBD |  |
| R7 | window=50 | seam_diff_max | TBD |  |
| R8 | trials=1000 | sec_per_trial | TBD |  |
| R9 | repeat run | hash_diff_count | TBD | expect 0 |

---
## Decisions (Populate After Evidence)
Format: DECISION: <statement>
- DECISION (R1): TBD
- DECISION (R2): TBD
- DECISION (R3): TBD
- DECISION (R4): TBD
- DECISION (R5): TBD
- DECISION (R6): TBD
- DECISION (R7): TBD
- DECISION (R8): TBD
- DECISION (R9): TBD

## Alternatives Considered (Populate)
- R1: {Heuristic variants, direct block bootstrap, stationary bootstrap}
- R2: {Keep float64, mixed precision selective}
- R3: {Pure numpy only, Cython, vectorized pandas}
- R4: {Feather, CSV streaming}
- R5: {ORM layer, COPY-like emulation}
- R6: {Custom binary key, truncated hash}
- R7: {Overlapping partial recompute vs full recompute}
- R8: {Parallelism vs sequential deterministic}
- R9: {RNG per component vs global seed tree}

## Open Follow-ups
Should be EMPTY before Phase 1. Populate then resolve.
- TBD

## Exit Criteria
- All DECISION lines filled
- Benchmark Data Template populated (no TBD for critical tracks R1–R5)
- Open Follow-ups empty or deferred explicitly in spec
- Constitution re-check passes

---
Generated: 2025-09-23
