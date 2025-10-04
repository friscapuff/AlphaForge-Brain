# Quickstart: NVDA 5-Year Backtest

This guide shows how to run an end-to-end backtest using the integrated 5-year NVDA dataset.

## 1. Prerequisites
- Python environment (project already pinned to Python 3.11)
- Dataset file: `NVDA_5y.csv` placed at: `./data/NVDA_5y.csv` (create `data/` if missing)
- Columns required: `timestamp,open,high,low,close,volume` (optional: `adj_close`)
- Timestamps may be in exchange local time; system will normalize to UTC.

## 2. Run a Sample Backtest
Use the existing run creation endpoint (example payload). Adjust dates to align with actual dataset bounds.

Example JSON (POST /runs):
```json
{
  "symbol": "NVDA",
  "timeframe": "1d",
  "start": 1609459200000,
  "end": 1735603200000,
  "provider": "local_csv",
  "indicators": [
    { "name": "sma", "params": { "window": 20 } },
    { "name": "ema", "params": { "window": 50 } },
    { "name": "atr", "params": { "window": 14 } }
  ],
  "strategy": { "name": "dual_sma", "params": { "fast": 20, "slow": 50 } },
  "risk": { "model": "fixed_fraction", "params": { "fraction": 0.1 } },
  "execution": {
    "commission_per_share": 0.0,
    "slippage_bps": 5,
    "borrow_bps": 0.0,
    "fill_price": "open_next",
    "slippage_model": { "model": "spread_pct", "params": { "spread_pct": 0.001 } }
  },
  "validation": { "permutation": { "n": 50 }, "block_bootstrap": { "n": 30, "block_size": 5 } },
  "seed": 42
}
```

Notes:
- `start` / `end` are epoch milliseconds in UTC.
- The system will slice the canonical NVDA dataset by these bounds; canonical dataset remains cached.

## 3. Monitor Progress
Two options:
1. One-shot flush (ETag cacheable): `GET /runs/{run_id}/events`
2. Long-lived incremental stream: `GET /runs/{run_id}/events/stream`

## 4. Retrieve Artifacts
List manifest:
```
GET /runs/{run_id}/artifacts
```
Download individual artifact (e.g. `summary.json`):
```
GET /runs/{run_id}/artifact/summary.json
```

Expected artifacts (names illustrative):
- `summary.json` (run summary & metrics subset)
- `metrics.json` (detailed metrics)
- `validation.json` (anomaly counters, events)
- `equity.parquet` (equity curve)
- `trades.json` (trade ledger)
- `manifest.json` (artifact manifest w/ hashes, data_hash, calendar_id)
- `plots.png` (optional visualization)

## 5. Determinism & Idempotency
- Repeating the same POST body with unchanged dataset yields the same `run_id` (hash reuse) and avoids redundant ingestion.
- Change detection: Modifying CSV contents changes the internal `data_hash` which cascades into new run hash.

## 6. Validation Summary
`validation.json` includes counters like:
```json
{
  "symbol": "NVDA",
  "data_hash": "<sha256>",
  "counters": {
    "duplicates_dropped": 0,
    "rows_dropped_missing": 0,
    "zero_volume_rows": 12,
    "future_rows_dropped": 0,
    "unexpected_gaps": 1
  },
  "expected_closures": 125,
  "unexpected_gaps": 1,
  "events": [ ... ],
  "generated_at": 1735603200000
}
```
A subset appears inline in `GET /runs/{run_id}` response under `validation_summary`.

## 7. Troubleshooting
| Issue | Cause | Action |
|-------|-------|--------|
| 404 on run retrieval | Wrong run_id | Verify returned run_id from creation response |
| Mismatch in expected rows | Date bounds outside dataset | Adjust `start`/`end` to dataset range |
| Zero metrics / empty trades | Strategy produced no signals | Verify indicator parameters |
| Unexpected duplicate count >0 | CSV contains repeated timestamps | Inspect raw file; confirm deterministic drop |

## 8. Next Steps
- Add additional symbols via data source registry.
- Extend indicators & strategies.
- Integrate performance benchmarking for ingestion time (FR-019 empirical baseline).

## 9. Make Target (Planned)
`make run-local-nvda` (or Windows PowerShell equivalent script) will: load dataset, run a canonical dual SMA backtest, and print artifact manifest path.

---
This quickstart aligns with deterministic, transparent ingestion and full pipeline reproducibility. Enjoy exploring NVDA performance.
