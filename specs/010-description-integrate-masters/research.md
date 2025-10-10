# Research: Advanced Statistical Validation Integration (Phase 0)

Feature: 010-description-integrate-masters
Date: 2025-10-10
Spec: specs/010-description-integrate-masters/spec.md
Plan: specs/010-description-integrate-masters/plan.md

## 1. Existing Validation & Metrics Inventory
| Area | Current Implementation | Key Files | Notes | Gaps for Feature |
|------|-----------------------|-----------|-------|------------------|
| Deterministic Backtest Metrics | Metrics pipeline computes Sharpe, CAGR, Max Drawdown, etc. | `alphaforge-brain/src/services/metrics.py`, `alphaforge-brain/src/domain/metrics/` | Deterministic hashes published via manifest. | Lacks statistical significance context and permutation evidence. |
| Monte Carlo / Bootstrap Validation | IID equity resampling for walk-forward caution. | `alphaforge-brain/src/domain/validation/monte_carlo.py` | Produces distribution histograms but assumes independence. | Needs Masters-style permutation engine with bar-level shuffling and re-optimisation. |
| Validation Manifest Persistence | Validation payload stored in SQLite `validation_results`, manifest JSON per run. | `alphaforge-brain/src/infra/orm/models.py`, `alphaforge-brain/src/services/manifests.py` | Stores scalar metrics and caution flags. | Schema missing p-values, permutation metadata, cross-validation diagnostics. |
| Mind Visualization | Displays validation charts from Monte Carlo results. | `alphaforge-mind/src/pages/backtest/validation-view.tsx`, `alphaforge-mind/src/services/api/backtests.ts` | Expects arrays of histograms & caution badges. | Needs UI for permutation distributions, Sharpe deflation, CPCV timelines, realism gauges. |

## 2. Masters Permutation Methodology Mapping
- **Permutation Scope**: Shuffle bar-level returns within in-sample and walk-forward segments independently to test null hypothesis of no edge.
- **Re-Optimisation Requirement**: For each permutation universe re-run optimisation pipeline using deterministic seed derived from `(run_seed, permutation_index)`.
- **Outputs Needed**:
  - P-value per segment, effect size (e.g., observed Sharpe vs permutation distribution).
  - Distribution summary (mean, std, percentile bands) for reporting & charting.
  - Metadata: permutation count executed vs requested, fallback reason if truncated.
- **Implementation Notes**:
  - Integrate with existing `domain/validation` orchestrator; extend to support chunked permutations to respect runtime SLA.
  - Ensure caching of base dataset & reuse of compiled indicators to avoid recomputation drift.
  - Deterministic seeding via new `PermutationSeedContext` helper binding to manifest.

## 3. Sharpe Bias Diagnostics (DSR/PSR)
- **Deflated Sharpe Ratio (DSR)**: Adjusts Sharpe for multiple trials; requires estimation of skewness/leptokurtosis.
- **Probabilistic Sharpe Ratio (PSR)**: Probability Sharpe exceeds benchmark threshold.
- **Inputs**: Observed Sharpe, sample size, moment estimates, number of trials (derived from strategy parameter grid + prior tests).
- **Integration Plan**:
  - Introduce `bias_adjustments.py` in validation domain returning DSR, PSR, caution flags.
  - Persist `assumed_trials` and `benchmark_sharpe` in manifest; expose to Mind for tooltips.
  - Extend test suite with deterministic synthetic series to validate closed-form outputs.

## 4. Cross-Validation Leakage Controls
- **Purged K-Fold**: Remove lookahead leakage with overlapping windows removed based on bar distance derived from strategy horizon.
- **Combinatorial Purged Cross-Validation (CPCV)**: Evaluate combinations of folds to reduce selection bias.
- **Implementation Steps**:
  - Represent fold definitions via structured model storing `train_range`, `test_range`, `purge_span`.
  - Provide fallback to CPCV when purge spacing insufficient; log justification.
  - Capture fold-level metrics and aggregated leakage score (0-1) to persist + display.

## 5. Execution Realism Enhancements
- **Transaction Cost Overlay**: Extend existing cost model to run deterministically per scenario; avoid double-counting when strategy already includes costs (flag via config).
- **Market Impact Model**: Parameterize via volume participation rate; compute slippage per trade bucket.
- **Liquidity Capacity Test**: Evaluate average daily volume vs order size; produce pass/fail & capacity ratio.
- **Outputs**: Structured `ExecutionRealismReport` with `status`, `warnings`, `assumptions` for manifest and API.

## 6. Persistence & Contract Impact
| Artifact | Change Needed | Backward Compatibility Strategy |
|----------|---------------|----------------------------------|
| SQLite `validation_results` | Add columns for `segment`, `p_value`, `effect_size`, `permutation_count`, `dsr`, `psr`, `cscv_bias`, `leakage_score`, `realism_status`. | Add nullable columns with default `NULL`; historical runs show neutral values. |
| Manifest JSON | Extend `validation` section with `permutation_summary`, `sharpe_adjustments`, `cross_validation`, `execution_realism`. | Default to placeholders when new modules disabled; include schema version bump. |
| API `GET /runs/{id}` | Add nested objects, maintain legacy keys. | Add new fields, keep existing ones untouched; document in OpenAPI & Quickstart. |
| SSE `validation.update` | Include new payload segments; ensure Mind handles incremental streaming order. | Use correlation IDs to align sections; Mind falls back to neutral display when missing. |

## 7. Observability & Performance Considerations
- Instrumentation: Add structured timings for permutation batches, cross-validation folds, realism models under `validation.*` span in structlog.
- Resource Tracking: Record CPU time + memory footprint for validation stage to feed FR-015 guard.
- Benchmark Plan: Create micro-benchmark harness in `scripts/bench/perf_run.py` capturing run duration with validation modules toggled.
- Alerting: Warn when permutation runtime exceeds configured SLA or when fallback heuristics triggered.

## 8. Risk Register
| Risk | Category | Impact | Likelihood | Mitigation | Trigger |
|------|----------|--------|------------|------------|---------|
| Permutation runtime explosion on large datasets | Performance | High | Medium | Adaptive permutation counts, SLA monitor, chunked execution. | Runs > 50k bars with full permutations. |
| Seed drift causing non-reproducible permutations | Determinism | High | Low | Centralize seed derivation, tests verifying reproduction. | Re-run permutations produce mismatched p-values. |
| Statistical library mismatch (DSR/PSR) | Correctness | Medium | Low | Cross-validate formulas against reference implementation (statsmodels/scipy). | Test suite delta vs reference > tolerance. |
| Mind visualization overload | UX | Medium | Medium | Progressive disclosure, lazy load charts, documentation. | SSE payload size > 1.5 MB or UI clutter feedback. |
| Double-counting execution costs | Business Logic | High | Medium | Detect existing cost config, skip overlays, warn user. | Strategy config includes cost_flag + realism overlay active. |
| Schema migration failure | Data Integrity | Medium | Low | Alembic migration with backfill script + rollback plan. | Migration fails in staging. |

## 9. Decision Log
| # | Decision | Rationale | Revisit Trigger |
|---|----------|-----------|-----------------|
| 1 | Use Masters permutation counts default 500 per segment | Balance statistical power vs runtime | Runtime SLA breach on 50k bar datasets. |
| 2 | Default significance threshold 0.01 | Align with institutional standards (FR-002) | User demand for less strict threshold. |
| 3 | Persist histograms as compressed parquet | Efficient storage vs JSON bulk | Storage limitations or Mind needing raw arrays inline. |
| 4 | Expose permutation histograms inline + artifact reference | Supports UI snapshots and external audit blobs simultaneously | Storage or bandwidth constraints tighten. |
| 5 | Provide toggles for each validation module via CLI + Mind UI | Allows phased rollout & debugging while maintaining determinism defaults | Consistent success and no regressions for 3 releases. |
| 6 | Execution realism limited to cost, impact, liquidity initially | Focus on most critical realism factors | Evidence of slippage from other sources (e.g., borrow constraints). |
| 7 | Neutral defaults for historical runs | Preserve compatibility and avoid reprocessing backlog | Decision to backfill historical data. |
| 8 | Bias flag threshold = CSCV-adjusted Sharpe ≤ observed Sharpe − 0.25 or ≥20% relative drop | Deterministic, business-approved cutoff for "material degradation" | Risk team revises tolerance bands. |
| 9 | Default purge span = max(30 calendar days, strategy lookback horizon) | Mirrors Masters methodology’s embargo guidance | Strategy team requests different baseline. |
| 10 | Execution realism guidance must include cost/impact deltas, capacity ratio, and remediation recommendation | Ensures guidance is actionable and testable | Product wants additional advisory dimensions. |
| 11 | Clarified 2025-10-10 that permutation histograms must ship inline **and** as artifact references, purge span defaults to time-based embargo (max(30D, lookback)), and validation toggles surface via CLI + Mind UI | Aligns feature scope with stakeholder expectations and closes lingering assumptions | Product or platform teams request alternative exposure or gating surfaces. |

## 10. Open Questions
None — clarified via 2025-10-10 follow-up (see Decision Log entries 4, 5, 9, 11).

## 11. Phase 0 Exit Criteria
- Validation inventory completed ✔️
- Methodology alignments documented ✔️
- Persistence/contract impacts enumerated ✔️
- Risks & decisions captured ✔️
- Open questions tracked (await responses)
