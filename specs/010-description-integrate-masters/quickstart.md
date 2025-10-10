# Quickstart: Advanced Statistical Validation

## 1. Enable Validation Modules (PowerShell)
```
$env:AF_VALIDATION_MODULES="permutation,dsr,psr,purged_kfold,cpcv,realism"
$env:AF_VALIDATION_PERMUTATION_COUNT=500
$env:AF_VALIDATION_SIGNIFICANCE_THRESHOLD=0.01
$env:AF_LEAKAGE_THRESHOLD=0.1
$env:AF_REALISM_CAPACITY_BPS_LIMIT=500
```
(Use `export` instead of `$env:` for bash/zsh shells.)

## 2. Run a Backtest with Validation Enabled
```
poetry run python scripts/bench/perf_run.py --iterations 1 --warmup 0 --keep-artifacts --output zz_artifacts/validation_smoke.json
```
This single-iteration harness exercises the Masters validation pipeline and keeps the generated artifacts instead of deleting them between runs. After completion you’ll find:
- `zz_artifacts/validation_smoke.json` summarising stage timings, module status, and SLA violations.
- A persistent run directory under `artifacts/<RUN_HASH>/` containing:
   - `validation/permutation/segment_in_sample.parquet`
   - `validation/permutation/segment_walk_forward.parquet`
   - `validation.json` + `validation_detail.json` (inline validation summary payloads)
   - Standard backtest artifacts (`summary.json`, `metrics.json`, `equity.parquet`, etc.).
The harness emits real validation spans but currently writes placeholder `validation_*` fields in `manifest.json`; refer to the smoke JSON and detail files for full metrics until the aggregator wiring lands.

## 3. Inspect Validation Summary via CLI
```
poetry run python alphaforge-brain/scripts/validation/show_summary.py --run-id <RUN_ID>
```
When the manifest includes Masters metadata, the CLI renders permutation segments, Sharpe deflation metrics, CPCV leakage scores, and execution realism diagnostics. Until the manifest upgrade is merged, use this CLI to confirm artifact presence and inspect module placeholders, then open `validation_detail.json` for the full metrics captured in the smoke run.

## 4. Run Validation Property Tests
```
poetry run pytest alphaforge-brain/tests/property/validation/test_permutation_distribution.py --no-cov
```
These Hypothesis-based tests ensure histogram counts match permutation executions, percentiles remain ordered, p-values sit within (0,1], and constant-return datasets collapse into a single histogram bin.

## 5. View in Mind UI
1. Start Brain API and Mind dev server (`poetry run uvicorn api.app:app --reload`; `pnpm --dir alphaforge-mind dev`).
2. Load the Backtest & Validation tab.
3. Confirm UI renders:
   - Permutation histograms with significance badges.
   - Sharpe deflation summary cards.
   - Cross-validation fold timeline.
   - Execution realism gauges and warnings.

## 6. Benchmark Validation Runtime
```
poetry run python scripts/bench/perf_run.py --iterations 3 --warmup 1 --validation-modules all
```
Outputs `zz_artifacts/perf_latest.json` with runtime of validation stage; alerts when >20% slower than baseline. Latest run clocks the Masters suite at ~1543 ms versus the 34 ms SLA budget, so plan remediation work accordingly.

## 7. Toggle Modules
- Disable modules individually by removing them from `AF_VALIDATION_MODULES`.
- Modules disabled still emit manifest entries showing `status: "omitted"`.

## 8. Rollback Procedure
1. Clear environment variables or set `AF_VALIDATION_MODULES=""`.
2. Re-run backtests; validation sections revert to historical behavior with neutral defaults.
3. Ensure migrations remain intact; no data loss as columns are nullable.

## 9. Troubleshooting
| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| Missing permutation artifacts | Validation module disabled or SLA fallback aborted run | Check `AF_VALIDATION_MODULES` and logs for fallback reason. |
| DSR/PSR show `null` | Observed Sharpe zero or insufficient observations | Verify run length; ensure moments computed. |
| Leakage score remains `null` | Purged folds disabled or failure in CPCV fallback | Confirm `purged_kfold` toggle; inspect logs. |
| Realism status `fail` unexpectedly | Strategy already includes costs causing double-count | Mark strategy config flag `costs_included=true`; rerun validation. |
| UI badges show "Data unavailable" | Mind build not updated | Update Mind branch `010-description-integrate-masters` and rebuild. |

## 10. Support Artifacts
- `research.md`: methodology & risk register.
- `data-model.md`: schema & contract changes.
- `contracts/`: JSON schemas/examples for API & SSE payloads.
- `tasks.md`: generated via `/tasks` process after plan completion.
