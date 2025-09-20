# Quickstart – Project A Backend (v1)

This guide shows how a client (future UI) would submit a backtest run and retrieve results.

> Contributor Environment Note
> Always work inside the Poetry virtual environment. Activate with `poetry shell` or prefix commands with `poetry run` (e.g. `poetry run pytest`). Avoid using `pip install` directly; instead edit `pyproject.toml` and run `poetry update` / `poetry install` so CI and all developers get identical dependency versions. A helper script (`scripts/env/check_env.py`) can be run via `poetry run python scripts/env/check_env.py` to validate the active interpreter, structlog version, and that required dev tools are present.

## 1. Create a Run
POST /runs
```json
{
  "symbol": "AAPL",
  "timeframe": "1h",
  "start": 1672531200000,
  "end": 1675209600000,
  "provider": "local",
  "indicators": [ { "name": "sma", "params": { "length": 20 } }, { "name": "sma", "params": { "length": 50 } } ],
  "strategy": { "name": "dual_sma", "params": { "fast": 20, "slow": 50, "threshold_bp": 0, "delay_bars": 0, "long_only": false } },
  "risk": { "name": "fixed_fraction", "params": { "fraction": 0.25, "max_leverage": 1.0 } },
  "execution": { "commission_per_share": 0.005, "slippage_bps": 1.5, "borrow_bps": 50, "fill_price": "open_next" },
  "validation": { "permutation": { "n": 100 }, "block_bootstrap": { "n": 100, "block_size": 24 } },
  "seed": 42
}
```
Response 201:
```json
{ "run_id": "UUID", "hash": "CONFIG_HASH", "status": "queued" }
```
If identical config re-submitted:
```json
{ "run_id": "UUID", "hash": "CONFIG_HASH", "status": "running", "reused": true }
```

## 2. Fetch Run Events (One‑Shot SSE Flush)
GET /runs/{run_id}/events returns a Server-Sent Events (SSE) sequence containing all currently buffered events for the run in deterministic order, then closes the connection. Re‑poll to get newly appended events until you observe a terminal event (`completed` or `cancelled`). No heartbeat spam; each event is stable and idempotent.

Example (completed run flush):
```
id: 0
event: stage
data: {"type":"stage","ts":"2024-01-01T00:00:00Z","data":{"run_hash":"abc123","state":"RUNNING"}}

id: 1
event: stage
data: {"type":"stage","ts":"2024-01-01T00:00:00Z","data":{"run_hash":"abc123","state":"VALIDATING"}}

id: 2
event: snapshot
data: {"type":"snapshot","ts":"2024-01-01T00:00:01Z","data":{"run_hash":"abc123","status":"COMPLETE"}}

id: 3
event: completed
data: {"type":"completed","ts":"2024-01-01T00:00:01Z","data":{"run_hash":"abc123","status":"COMPLETE"}}
```

Example (cancelled run flush):
```
id: 0
event: stage
data: {"type":"stage","ts":"2024-01-01T00:00:00Z","data":{"run_hash":"abc123","state":"RUNNING"}}

id: 1
event: snapshot
data: {"type":"snapshot","ts":"2024-01-01T00:00:01Z","data":{"run_hash":"abc123","status":"RUNNING"}}

id: 2
event: cancelled
data: {"type":"cancelled","ts":"2024-01-01T00:00:02Z","data":{"run_hash":"abc123","status":"CANCELLED"}}
```

Polling guidance:
- Poll interval ramp: 0.5s -> 1s -> 2s (cap) until terminal event.
- Use the last numeric id to avoid re-rendering older events; on next fetch discard events with id <= last seen.
- Determinism: identical configs (same run hash) always yield identical ordered event lists.

## 3. Poll Run Detail
GET /runs/{run_id}
```json
{
  "run_id": "UUID",
  "status": "completed",
  "hash": "CONFIG_HASH",
  "metrics_summary": { "total_return": 0.12, "sharpe": 1.4, "max_drawdown": -0.08 },
  "artifacts": { "manifest_path": "/runs/UUID/manifest.json" }
}
```

## 4. Download Artifacts
GET /runs/{run_id}/artifacts -> manifest JSON listing hashed files.
GET /runs/{run_id}/artifact/equity.parquet -> equity curve.

Each new run's `manifest.json` now includes:
```
{
  "run_hash": "...",
  "created_at": "2024-01-02T00:00:00Z",
  "chain_prev": "<previous_manifest_hash>|null",
  "manifest_hash": "<this_manifest_canonical_hash>",
  "files": [ {"name": "summary.json", "sha256": "...", "size": 512, "path": "<run_hash>/summary.json" }, ... ]
}
```
`chain_prev` forms an integrity chain across sequential runs allowing tamper detection (hash mismatch breaks traversal). Re-running an identical config reuses the same run directory & manifest; the `manifest_hash` and `chain_prev` remain stable (idempotent).

## 5. Candle & Feature Preview
GET /candles?symbol=AAPL&timeframe=1h&start=...&end=...
GET /features?symbol=AAPL&timeframe=1h&indicators=%5B%7B%22name%22:%22sma%22,%22params%22:%7B%22length%22:20%7D%7D%5D

## 6. Presets
Save a parameter preset:
POST /presets
```json
{ "name": "dual_sma_hourly_default", "config": { ... RunConfig minus seed ... } }
```
Fetch:
GET /presets/dual_sma_hourly_default

## 7. Cancellation
POST /runs/{run_id}/cancel  (idempotent, sets cancel flag; run emits cancelled event)

## 8. Error Envelope
Example invalid param:
```json
{ "error": { "code": "INVALID_PARAM", "message": "fast must be < slow", "details": {"field": "strategy.params.fast"}, "retryable": false } }
```

## 9. Deterministic Re-run
Re-submit identical body: server returns existing run (status may advance) with `reused: true`.

## 10. Retention Behavior
After 101st completed run, oldest run directory and DB row removed. Manifest hash ensures integrity before deletion optional.

---
This quickstart covers the primary lifecycle: submit, stream, inspect, download artifacts, manage presets, and cancel.
