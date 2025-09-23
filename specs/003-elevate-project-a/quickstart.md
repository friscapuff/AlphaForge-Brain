# Quickstart: Truthful Backtest Run (NVDA)

## Prerequisites
- Python 3.11 environment (mypy/ruff/pytest installed)
- NVDA 5-year dataset ingested per Spec 002 (has data_hash)
- Type Hygiene Gate (Phase 3.4H) PASSED (zero mypy errors, no unused ignores; CI enforced). Maintain zero-error baseline when adding API endpoints.
- Matplotlib now a core dependency (no visualization extra required) ensuring `plots.png` always produced.

## 1. Prepare Run Configuration (example JSON - baseline, no walk-forward)
```json
{
  "dataset": {"path": "data/nvda_5y.parquet", "data_hash": "<sha256>", "calendar_id": "XNYS"},
  "strategy": {"id": "sma_cross", "required_features": ["sma_fast","sma_slow"], "parameters": {"fast": 20, "slow": 50}},
  "features": [
    {"name": "sma_fast", "version": "1.0", "params": {"window": 20}, "shift_applied": true},
    {"name": "sma_slow", "version": "1.0", "params": {"window": 50}, "shift_applied": true}
  ],
  "execution": {"fill_policy": "NEXT_BAR_OPEN", "lot_size": 1, "rounding_mode": "ROUND"},
  "costs": {"slippage_bps": 1.0, "fee_bps": 0.5, "borrow_cost_bps": 50},
  "validation": {"permutation_trials": 100, "seed": 12345, "caution_p_threshold": 0.1},
  "causality_shift": true,
  "strict_causality_guard": true
}
```

## 2. Submit Run
Use HTTP client (curl/httpie) against POST /runs with above JSON.
Expect response containing `run_id` and `run_hash`.

## 3. Stream Events
Connect to `/runs/{run_id}/events?stream=true` and observe:
- phase_transition events following ordered phases
- heartbeat ≤15s
- summary_snapshot with trades count and (post-permutation) p_value

## 4. Retrieve Artifacts
GET `/runs/{run_id}` to list artifacts. Download `manifest.json`, `equity.parquet`, `trades.parquet`, `plots.png`.

## 5. Verify Determinism
Resubmit identical JSON (optionally Idempotency-Key header). Compare returned `run_hash` and artifact SHA-256 values; they must match.

Deterministic Anomaly Counters:
When calling `GET /runs/{run_id}?include_anomalies=true` the response now ALWAYS includes `summary.anomaly_counters` (empty object if no anomalies). This removes conditional response shape drift during early ingestion phases.

## 6. Inspect Causality
Check metrics.json: ensure `future_access_violations == 0`. Any non-zero indicates strategy bug.

## 7. Evaluate Statistical & Robustness Validity
Baseline permutation fields: `p_value`, `extreme_tail_ratio`. A low p_value (e.g. < caution threshold) suggests observed performance unlikely under null shuffles. extreme_tail_ratio > 1 indicates heavier favorable tail than null distribution. Robustness composite only appears when walk-forward enabled.

## 8. Optional Skip Permutation
Set `permutation_trials` to 0 → placeholder fields appear; determinism unaffected.

## 9. Plot Review
Open plots.png: equity curve + drawdown subplot. Visual anomalies (gaps, spikes) should correlate with ledger events.

## 10. Replay Guarantee
Store manifest.json. On future environment, re-run with same dataset path & hash → identical run_hash and file checksums.

Replay Verification Script:
After completion of polish task T075 you can run `python scripts/verify_replay.py` to automatically perform two back-to-back runs of a minimal config and assert identity of run hash + artifact hashes.

## 11. Enable Walk-Forward Validation (FR-046..FR-048)
Add a `walk_forward` block to configuration:
```json
  "walk_forward": {
    "segment": {"train_bars": 252*2, "test_bars": 63, "warmup_bars": 20},
    "optimization": {"enabled": true, "param_grid": {"fast": [10,20,30], "slow": [40,50,60]}},
    "robustness": {"compute": true}
  }
```
Guidelines:
- train_bars + test_bars must fit within dataset; segments advance by test_bars (sliding).
- warmup_bars (optional) excluded from metrics but provided to feature initializers.
- Overlapping train/test (other than warm-up) rejected.

Artifacts Added:
- `walk_forward.json` (per-segment metrics, boundaries, chosen params hash)
- Summary includes: `oos_consistency_score`, `proportion_of_profitable_oos_segments`, `robustness_score`.

Interpreting Robustness Fields:
- oos_consistency_score: Lower dispersion value = more stable OOS performance (e.g. Coefficient of Variation of segment Sharpe or returns).
- proportion_of_profitable_oos_segments: Fraction of segments with positive OOS return.
- robustness_score: Weighted composite (defaults: p_value_weight=0.4 inverse scaled, stability=0.3, profitability=0.2, tail=0.1). Higher is better (documented in `research.md`).

Example SSE Snapshot (truncated):
```json
{ "event":"summary_snapshot", "data": { "p_value":0.032, "extreme_tail_ratio":1.7, "oos_consistency_score":0.22, "proportion_of_profitable_oos_segments":0.75, "robustness_score":0.68 } }
```

## 12. Troubleshooting
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Different run_hash after replay | Dataset changed or float options not applied | Verify data_hash & global float settings |
| SSE stream no terminal event | Server interruption | Check logs; run should be marked FAILED with partial artifacts |
| Non-zero future_access_violations | Strategy accessed future data | Audit signal function; use debug PERMISSIVE mode locally |
| High p_value caution | Strategy not statistically significant | Iterate or collect more validation methods |
| Overlap split error | Invalid walk-forward config | Adjust train/test so train_end < test_start |
| Missing robustness_score | Walk-forward disabled | Add walk_forward block with robustness.compute true |
| anomaly_counters missing | Did not pass include_anomalies flag | Re-issue GET with `?include_anomalies=true` (empty object still counts) |
| Performance tests slow | First warm cache population | Re-run tests once data/feature caches filled; see `tests/perf/` harness |
| Mypy errors appear before API dev | Gate not satisfied | Complete T080–T086 hygiene tasks before exposing endpoints |
| Import errors in tests | Missing tests/conftest.py path setup | Ensure Phase 3.4H T080 applied adding PYTHONPATH fix |
| Low robustness_score despite low p_value | Unstable OOS segments | Investigate per-segment variance in walk_forward.json |

