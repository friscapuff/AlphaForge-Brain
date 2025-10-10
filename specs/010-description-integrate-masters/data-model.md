# Data Model: Advanced Statistical Validation

Feature: 010-description-integrate-masters
Spec: specs/010-description-integrate-masters/spec.md
Plan: specs/010-description-integrate-masters/plan.md
Research: specs/010-description-integrate-masters/research.md

## 1. Canonical Entities
| Entity | Purpose | Key Fields | Notes | Hash Participation |
|--------|---------|------------|-------|--------------------|
| `PermutationValidationResult` | Captures Masters permutation outputs per segment (in-sample, walk-forward). | `run_id`, `segment_id`, `permutation_count`, `p_value`, `effect_size`, `distribution_path`, `seed_root`, `fallback_reason?` | New table / manifest section; distribution persisted as artifact (Parquet). | Participates in validation manifest signature v2 via artifact references and gating metadata tracked in `validation_significance`. |
| `SharpeBiasAdjustment` | Stores DSR/PSR adjustments and underlying trial assumptions. | `run_id`, `observed_sharpe`, `deflated_sharpe`, `probabilistic_sharpe`, `assumed_trials`, `benchmark_sharpe`, `skewness`, `kurtosis` | Derived from metrics; persisted in validation table extension. | Excluded from existing run hashes; separate validation signature tracked. |
| `CrossValidationFold` | Describes purged or CPCV fold boundaries and leakage metrics. | `fold_id`, `run_id`, `mode`, `train_start`, `train_end`, `test_start`, `test_end`, `purge_span`, `leakage_score`, `performance_metrics` | Stored as JSON blob per fold; aggregated leakage score surfaced in manifest. | Not hashed (validation-only). |
| `ExecutionRealismReport` | Summarizes transaction cost, impact, and liquidity diagnostics. | `run_id`, `status`, `transaction_cost_bps`, `impact_bps`, `capacity_ratio`, `warnings[]`, `assumptions` | Persisted as JSON within manifest + SQLite column for status. | Hash unaffected; status feeds promotion gating defined in `docs/governance/retention_policy.md`. |
| `ValidationConfig` (extended) | Captures module toggles & thresholds. | `permutation_enabled`, `permutation_count`, `significance_threshold`, `dsr_enabled`, `psr_enabled`, `purged_kfold_enabled`, `cpcv_enabled`, `realism_enabled` | Already serialized with run config; extend schema to include new flags & defaults. | Config signature contributes to existing determinism hash. |

## 2. SQLite Schema Changes (Brain)
| Table | Change | Type | Backward Compatible? |
|-------|--------|------|----------------------|
| `validation_results` | Add columns: `segment_id TEXT`, `validation_type TEXT`, `p_value REAL`, `effect_size REAL`, `permutation_count INTEGER`, `dsr REAL`, `psr REAL`, `bias_flag BOOLEAN`, `leakage_score REAL`, `realism_status TEXT`, `metadata JSON` (SQLite JSON1). | Alembic migration adding nullable columns + JSON1 extension guard. | Yes, defaults to `NULL` / `"neutral"`. |
| `runs` (manifest snapshot) | Extend `validation_manifest` JSON to include new sections; add `validation_schema_version INTEGER` (defaults to 2 for new runs, 1 for legacy). | Alembic migration with default 1. | Yes; historical runs default to version 1 until backfilled. |

## 3. Manifest & Artifact Layout
```
artifacts/
  runs/{run_hash}/
    validation/
      permutation/
        segment_{id}.parquet  # histogram of permuted Sharpe/CAGR values
      cscv/
        folds.parquet         # fold metrics & leakage scores
      realism.json            # execution realism report (structured)
```
- Manifest `validation` section references above artifacts via relative paths + SHA256 for audit and drives retention gating checks.
- Add `validation_significance` enum (`pass|caution|fail`) derived from dominant module outcome; documented governance workflow lives in `docs/governance/retention_policy.md`.
- Document artifact schema versions for parity tests.

## 4. API & SSE Contract Extensions (Brain → Mind)
| Endpoint/Event | Payload Section | Description | Compatibility |
|----------------|-----------------|-------------|---------------|
| `GET /api/v1/runs/{run_id}` | `validation.permutation` | Object with `segments[]` (p-value, effect size, histogram summary, artifact path) | Additive; default empty array. |
| `GET /api/v1/runs/{run_id}` | `validation.bias_adjustments` | Includes DSR, PSR, assumed trials, benchmark sharpe, status label. | Additive; defaults to neutral values or omitted when module disabled. |
| `GET /api/v1/runs/{run_id}` | `validation.cross_validation` | Contains mode (`purged_kfold` or `cpcv`), leakage score, folds summary (id, period, metric deltas). | Additive; empty when disabled. |
| `GET /api/v1/runs/{run_id}` | `validation.execution_realism` | Surface realism status, cost/impact/capacity metrics, warnings list, assumptions. | Additive. |
| SSE `validation.update` | Extend event payload to stream each section as ready with `correlation_id`, `section`, `payload`. | Additive; Mind handles by section name fallback to placeholders. |

## 5. Mind Data Shapes
| Component | Expected Data | Notes |
|-----------|---------------|-------|
| Permutation chart | `segments[].histogram` (bucket counts or density), `p_value`, `threshold`, `effect_size`. | Accepts aggregated hist for rendering; fall back to summary if artifact not yet fetched. |
| Sharpe diagnostics panel | `bias_adjustments.deflated_sharpe`, `probabilistic_sharpe`, `assumed_trials`, tooltip strings. | Display pass/caution/fail badges with tooltip. |
| Cross-validation timeline | `folds[]` with `mode`, `train_range`, `test_range`, `leakage_score`, `performance.metrics`. | Provide timeline view; highlight folds above leakage threshold. |
| Execution realism gauges | `execution_realism.transaction_cost_bps`, `impact_bps`, `capacity_ratio`, `status`, `warnings`. | Use gauge charts; show warnings banner when status != pass. |
| Toggle controls | `validation_config` synthesised from run + user settings. | Respect deterministic defaults; store user preference separately without altering run determinism. |

## 6. CLI / SDK Metadata
- `alphaforge-brain/scripts/bench/perf_run.py` persists `zz_artifacts/validation_smoke.json` capturing module spans and validation metadata; `alphaforge-brain/scripts/validation/show_summary.py` prints schema v2 payloads for CLI consumption and sign-off reviews.
- SDK (if any) exposes `run.validation` dataclass mirroring API structure; update type hints accordingly.
- Provide helper to print validation summary table with significance icons.

## 7. Feature Flags & Configuration
| Flag/Config | Default | Description |
|-------------|---------|-------------|
| `AF_VALIDATION_PERMUTATION_COUNT` | 500 | Number of permutations per segment; fallback adjusts downward but records executed count in manifest + smoke artifacts. |
| `AF_VALIDATION_SIGNIFICANCE_THRESHOLD` | 0.01 | Default significance threshold; persisted in config metadata. |
| `AF_VALIDATION_MODULES` | `"permutation,dsr,psr,cpcv,realism"` | Comma-separated toggles enabling modules; CLI + Mind surface toggles. |
| `AF_REALISM_CAPACITY_BPS_LIMIT` | 500 | Maximum acceptable combined cost/impact before fail. |
| `AF_LEAKAGE_THRESHOLD` | 0.1 | Leakage score threshold for caution/fail labeling and retention gating. |

## 8. Backward Compatibility & Migration Strategy
- Alembic migration adds nullable columns and sets `validation_schema_version=2` for new runs; historical runs remain version 1 with neutral defaults.
- API serialization only emits new sections when data present; Mind treats missing sections as "not available" badges.
- SSE clients upgrade path: subscribe to new `section` names; fallback uses default copy until Mind update deployed.
- Provide migration script to backfill minimal placeholders for high-value historical runs if required (optional follow-up task).

## 9. Rejected Alternatives
| Alternative | Reason Rejected |
|-------------|-----------------|
| Store permutation histograms inline as JSON arrays | Payload too large; prefer Parquet artifacts + summary stats. |
| Force CPCV always | Runtime cost high; keep purged K-Fold default with CPCV fallback. |
| Persist realism metrics per trade | Increases storage dramatically; summary-level metrics sufficient for validation gating. |

## 10. Outstanding Questions
- What SLA target will replace the interim 34 ms guardrail once Masters runtime profiling completes? Performance tuning continues under Phase 3.5 follow-up.
- How aggressively should permutation counts scale for replay/backfill scenarios to balance runtime vs. statistical power? Use insights from `docs/operations/validation_backfill.md` dry-runs to calibrate defaults.
