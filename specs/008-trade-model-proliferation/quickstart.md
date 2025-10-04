# Quickstart: Unified Trade & Equity Consistency

## 1. Enable Feature Flags
```
export AF_UNIFIED_TRADES=1
export AF_EQUITY_NORMALIZER_V2=1
```
(Windows PowerShell)
```
$env:AF_UNIFIED_TRADES=1
$env:AF_EQUITY_NORMALIZER_V2=1
```

## 2. Run Baseline vs New Comparison
1. Disable flags; run 3 baseline backtests → produce `artifacts/baseline_hashes_v1.json`.
2. Enable flags; re-run same configs → produce `artifacts/compare_hashes_v2.json`.
3. Diff equity & metrics hashes; only equity hash expected difference (normalization) once Phase 3 active.
4. During Phase 3 the run record includes a `normalized_equity_preview` (rows + median_nav) for smoke validation; hashes remain legacy until cleanup phase.

## 2a. Phase 3 Equity Normalization Workflow (Compare Mode)
```
# Flag OFF (legacy scaled path)
$env:AF_EQUITY_NORMALIZER_V2=0
python -m scripts.run_backtest --config example.json

# Flag ON (adds normalized_equity_preview, hashes still legacy)
$env:AF_EQUITY_NORMALIZER_V2=1
python -m scripts.run_backtest --config example.json
```
Inspect run record (API or artifact JSON) for `normalized_equity_preview`:
```
"normalized_equity_preview": {
	"rows": 251,
	"median_nav": 987.23,
	"median_value": 987.23,
	"scaled": false,
	"scale_factor": 1
}
```
`median_nav` (legacy naming retained) and `median_value` are both present during the compare phase. `scaled=false` plus `scale_factor=1` indicates no hidden 1_000_000 factor remains. Median NAV << 1_000_000 indicates successful normalization (removal of arbitrary scaling).

### 2b. Upcoming Transition (Hashing Normalized Equity)
Planned flag (placeholder now present in `settings/flags.py`):
```
export AF_EQUITY_HASH_V2=1   # Linux/macOS
$env:AF_EQUITY_HASH_V2=1     # PowerShell
```
When Phase 3.5 / early Phase 4 tasks land, enabling this flag will switch the equity hash computation to use the normalized series. Until then the flag is inert and safe to ignore.

## 3. Migration Dry-Run
```
python scripts/migrations/unify_trades.py --dry-run --output artifacts/migration/unified_trades_report.json
```
Outputs:
- stdout summary table
- JSON report (counts transformed/skipped)

## 4. Validation Caution Gating
When validation p-value < configured threshold:
- API payload includes `"validation_caution": true` and list of triggering metric names.
- Retention promotion logic ignores caution runs.

## 5. Optimization Warning
If walk-forward optimization grid detected (and feature deferred):
- `advanced.warnings` contains an object: `{ code: "OPTIMIZATION_DEFERRED", combinations: <n>, limit: <limit> }`

Set a grid size limit via environment variable (default 0 = unlimited):

PowerShell (Windows):
```
$env:AF_OPTIMIZATION_MAX_COMBINATIONS=1000
```

Shell (Linux/macOS):
```
export AF_OPTIMIZATION_MAX_COMBINATIONS=1000
```

## 6. Drawdown Epsilon Override
```
export AF_DRAWDOWN_EPSILON=1e-8
```
Adjust only if floating precision differences appear across environments.

## 7. Rollback
- Disable flags → legacy trade models & scaling restored.
- Re-run determinism regression tests.

## 8. Expected Hash Behavior Summary
| Phase | equity_signature | metrics_signature | run_hash |
|-------|------------------|-------------------|----------|
| Pre-refactor | legacy | legacy | stable |
| After Phase 2 | unchanged | unchanged | stable |
| After Phase 3 | changed (documented) | unchanged | stable |
| Phase 3.5 (AF_EQUITY_HASH_V2=1) | normalized series (new) | unchanged | stable |
| After Phase 7 | stable new | stable new | stable |

## 9. Troubleshooting
| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Unexpected metrics hash diff | Legacy vs new metrics path mixed | Ensure only metrics_core imported |
| Drawdown validator failures | Epsilon too strict | Increase `AF_DRAWDOWN_EPSILON` slightly |
| Caution flag missing | Threshold not configured or validation disabled | Check ValidationConfig values |
| Optimization warning absent | Grid size below limit / flag disabled | Verify param grid enumeration |
| Normalized preview missing | Flag not exported or run reused cached record | Clear in-memory registry or change config |

## 10. Support Artifacts
- `research.md` for baseline references
- `data-model.md` for entity mapping
- `tasks.md` for implementation sequence
- `contracts/` concrete JSON examples (`fill.example.json`, `completed_trade.example.json`, `equity_bar.example.json`, `run_payload.example.json`) – use these as authoritative field references during client integration.

---
Generated 2025-10-01
