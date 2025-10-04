# Project A Backend (Single-User Studio Engine) – Execution Plan (v1)

Goal: Provide a deterministic, low-latency single-user backtest + validation engine exposed purely via REST + SSE so a TradingView‑like UI can submit chart state (symbols, timeframe, indicators, strategy params) and receive an idempotent run producing metrics, artifacts, and streaming progress/events.

## High-Level Flow
data -> feature/indicator computation (causal +1 bar shift) -> strategy signal generation -> risk sizing -> execution simulator (T+1 fills + costs) -> metrics aggregation -> validation workflows (optional) -> artifact generation -> retention & listing.

## Core Design Principles
1. Determinism: Every run identified by a hash of (data slice refs + configs + code version + seed). Idempotent POST returns existing run if hash collides.
2. Causality Enforcement: All features/indicators are shifted forward one bar before availability; strategy only sees data up to previous bar.
3. Composability: Pluggable registries (data providers, indicators, cost models, risk sizing algorithms, validation methods).
4. Streaming Transparency: SSE emits lifecycle: created -> data_loaded -> features_done -> strategy_done -> execution_done -> metrics_done -> validation_done -> artifacts_ready -> completed.
5. Minimal External Dependencies: Local filesystem + SQLite + Parquet/CSV; no cluster orchestration needed for v1.
6. Single-User Security: Lightweight static token auth + path sandboxing.
7. Reproducibility: Manifest with SHA-256 of each artifact + config snapshot + environment fingerprint (Python version, package hashes if/when code implemented later).

## Module Responsibilities

### 1. Data Layer
Responsibilities:
- Normalize and cache candles (OHLCV) for requested symbol + timeframe.
- Apply corporate action adjustments (split/dividend) if provider supplies raw.
- Calendar & timezone alignment (exchange calendar; drop/forward fill partial sessions policy configurable).
- Provide slicing APIs (inclusive start/end) returning Arrow Table / JSON (chart-friendly) subsets.
- Maintain provider registry: {id, type (local, remote), granularity supported, latency rating}.
Inputs: symbol(s), timeframe, date range, provider id.
Outputs: canonical candle frame with schema: [ts_utc (int64 ms), open, high, low, close, volume, vwap?].
Edge Cases: missing bars (gap tagging), daylight saving transitions, partial trading days.

### 2. Feature / Indicator Registry
Responsibilities:
- Declarative registration: name, version, required columns, params schema, output columns, window length.
- Automatic +1 bar causal shift (store raw result, shifted view exposed).
- Compute dependency graph (e.g., SMA of typical price requiring (high, low, close)).
- Caching keyed by (indicator hash, data segment hash).
Inputs: Candle frame slice, indicator configs list.
Outputs: Feature frame (aligned by ts_utc) with only shifted values exposed to downstream modules.
Edge Cases: Warmup period (initial window < full window) -> mark values as null until fully formed; shift should preserve nulls.

### 3. Strategy Framework
Responsibilities:
- Base Strategy interface: init(config), on_bar(state)-> signal (long/short/flat, size_hint?).
- Access only allowed columns (candles + shifted features). No lookahead.
- Example Dual SMA Strategy: signal = cross(SMA_fast, SMA_slow) with configurable lengths.
Inputs: Feature-enhanced frame, strategy config (name, params).
Outputs: Raw directional signals timeline (e.g., -1, 0, +1) plus optional target leverage.
Edge Cases: Overlapping signals, flat periods, missing feature values early.

### 4. Risk Sizing Module
Responsibilities:
- Convert raw signals to position targets using chosen sizing policy.
- Implemented models:
	- fixed_fraction: allocate fixed fraction of equity when signal != 0.
	- volatility_target: scales base fraction by target_vol / realized_vol (rolling stdev of returns) with clamping and early-bar suppression.
	- kelly_fraction: dampened Kelly fraction (p - (1-p)/R) * base_fraction, clamped to [0,1].
- Hooks/placeholders: future max position caps.
Inputs: Signals, price series (for volatility estimation), sizing config.
Outputs: Target position series (signed notional fraction) per bar.
Edge Cases: Insufficient history -> near-zero sizing sentinel; realized_vol=0 -> fallback minimal sizing to avoid div-by-zero.

### 5. Execution Simulator
Responsibilities:
- T+1 fill model: Orders derived from change in target position at bar t execute at bar t+1 open (or VWAP approximation) if exists; last bar cannot fill beyond dataset.
- Cost Models: commission (bps or per share), spread (half-spread slippage), borrow fee for short positions (annualized rate prorated), participation / impact via adapters.
- Slippage adapters applied before generic bps slippage & fee:
	- spread_pct: adjusts execution price by half the configured fractional spread in direction of trade.
	- participation_rate: impact proportional to (order_qty / bar_volume) * participation_pct capped at 1.0.
- Position Accounting: holdings, cash, realized/unrealized PnL, fees, slippage, borrow accrual daily.
Inputs: Target position series, candle frame, execution config (cost params).
Outputs: Executed trades list, per-bar portfolio state (position, cash, equity, fees_accum).
Edge Cases: Illiquid bar (zero volume) -> skip fill? configurable; dataset end truncation; fractional shares (allow decimals) vs integer flag.

### 6. Metrics Module
Responsibilities:
- Compute per-run summary: total_return, CAGR (if multi-year), volatility (annualized), Sharpe, Sortino, max_drawdown, avg_drawdown, drawdown_duration_stats, turnover, exposure %, win_rate, payoff_ratio, trade_count.
- Equity path & drawdown series.
- Rolling metrics window (e.g., 63-day rolling Sharpe) optional.
Inputs: Executed portfolio state, trades list.
Outputs: metrics JSON + time series (equity.csv/parquet, drawdown.csv/parquet).
Edge Cases: Zero volatility periods -> Sharpe NaN; fewer than 2 trades.

### 7. Validation Module
Responsibilities:
- Optional post-run statistical robustness checks.
- Permutation Test: shuffle signal order preserving returns distribution (N permutations).
- Block Bootstrap: resample contiguous blocks of returns preserving autocorrelation.
- Walk-Forward Optimization (WFO): segmented in-sample/out-of-sample: run windowed strategy param search (future extension placeholder) vs for v1 maybe just partition reporting.
- Monte Carlo Equity Resampling: randomizing trade sequence / slippage noise.
Inputs: Original trades/equity, validation config.
Outputs: Distribution stats (p-values, percentile bands), validation artifacts files.
Edge Cases: Insufficient data length for block size; N=0 skip.

### 8. Backtest Orchestrator
Responsibilities:
- State machine controlling stages; emits progress events.
- Dependency injection: passes around validated config objects.
- Orchestrates caching (re-use candles/features if hash matches) to reduce latency.
- Failure handling & early cancellation (cancel flag check between stages).
Inputs: Run request config.
Outputs: Run record updates, events, final artifacts.

### 9. Runs API
Operations:
- POST /runs : create (idempotent) -> {run_id, status, hash}.
- GET /runs : list (most recent first, limited by retention 100).
- GET /runs/{id} : detail (config, status, metrics summary link, artifacts manifest).
- POST /runs/{id}/cancel : request cancellation (idempotent; no-op if already terminal).
Idempotency: Client may send Idempotency-Key header; server returns existing run if identical hash.
Statuses: queued, running(stage_name), completed, failed(error_code), cancelled.

### 10. Event Stream (SSE)
Endpoints:
- GET /runs/{id}/events (flush) supports `after_id` and ETag for caching; `Last-Event-ID` backward compatible.
- GET /runs/{id}/events/stream provides long-lived incremental stream with heartbeats & resume via Last-Event-ID.
Event Types: heartbeat, progress, stage, warning, error, completed, cancelled.
Payload Base Fields: {run_id, ts, type, seq, data}.
Heartbeat Interval: 2s when idle.

### 11. Artifacts Module
Responsibilities:
- Write: summary.json, metrics.json, equity.parquet (and .csv), drawdown.parquet, trades.parquet, validation_summary.json, plots.png (optional), manifest.json including SHA-256 for each file + config hash + created_at.
- Provide retrieval endpoints (GET /runs/{id}/artifacts, GET /runs/{id}/artifact/{name}).
- Manifest links size & mime-type.
Retention: Maintain index ordered by completed_at; trim oldest beyond 100, deleting artifact directory.

### 12. Presets & Retention
Responsibilities:
- Save named parameter presets: strategy config + indicator list + risk + execution + validation flags.
- GET /presets, POST /presets, GET /presets/{name}, DELETE /presets/{name}.
- Distinct from run retention (only last 100 run histories kept; presets persistent until deleted).

## Cross-Cutting Concerns
Logging: Structured JSON logs per stage; correlation id == run_id.
Errors: Unified error model {code, message, details?, retryable?}.
Time Handling: All internal times UTC epoch ms.
Randomness: Single RNG seed per run; submodules derive via hash(seed + module_name).

## Data Contracts (Preliminary Types)
RunConfig: { symbol, timeframe, start, end, provider, indicators: [ {name, params} ], strategy: {name, params}, risk: {name, params}, execution: {slippage_bps?, commission_per_share?, borrow_bps?}, validation: { permutation?: {n}, block_bootstrap?: {n, block_size}, monte_carlo?: {n}, wfo?: {windows? placeholder} }, seed, presets_ref? }
RunRecord: { run_id, hash, status, created_at, updated_at, config_ref, artifacts?: {...}, metrics_summary?: {...} }
SignalSeries: array[{ts, signal}]; PositionTargets: array[{ts, target_notional_pct}]; Trade: {ts, side, qty, price, fee, slippage, pnl_realized}; PortfolioBar: {ts, position, price_ref, mv, cash, equity, fees_cum, pnl_unrealized}.
MetricsSummary: { total_return, max_dd, sharpe, sortino, vol, trade_count, win_rate, cagr?, exposure_pct, turnover, timestamp }.
Event: { run_id, seq, ts, type, stage?, progress? (0-1), message?, data? }.
ArtifactManifest: { run_id, files: [ {name, path, sha256, size, mime?} ], config_hash, created_at, chain_prev?, manifest_hash }.

## State Machine Stages
1. init
2. data_loading
3. feature_compute
4. strategy
5. risk_sizing
6. execution
7. metrics
8. validation (optional/skipped)
9. artifacts
10. completed

## Cancellation Model
User POST /runs/{id}/cancel sets cancel_requested=true (idempotent). Orchestrator checks between stages & before long loops; emits cancelled event and marks status=cancelled. Repeat requests after terminal state return 202 with current status (v1 behavior) to remain idempotent.

## Future Hooks (Out of Scope v1, placeholders only)
- Multi-symbol portfolios.
- Intraday corporate action adjustments.
- Portfolio-level hedging strategies.
- Live paper trading bridge.

---
NEXT: Flesh out data models, endpoints, OpenAPI, events schema, execution semantics, validation config, artifacts & retention details.

---
## Implementation Progress Log (Rolling)

### Completed Milestones (as of 2025-09-21)
- Ingestion Baseline & Benchmarking: Added `scripts/bench/ingestion_perf.py` producing JSON + optional Markdown and a baseline diff tool `ingestion_baseline_diff.py` to enforce deterministic row counts and data hash.
- Timestamp Normalization Consolidation: Introduced central `to_epoch_ms` utility handling naive vs tz-aware, DST ambiguous/nonexistent times, NaT preservation, optional future clipping; refactored ingestion & synthetic data paths to use it exclusively.
- Provenance Fallback & Observability: Artifact writer now guarantees `data_hash` and `calendar_id` in manifests with structured logging event (`writer.provenance.fallback`) on metadata retrieval failure.
- Anomaly Counters Surfacing: Validation summary and run detail now expose `anomaly_counters` (e.g., `unexpected_gaps`, `duplicates_dropped`) when available; tests assert presence under `include_anomalies=true`.
- Retention Idempotency: Run/artifact retention logic refactored to track prior removal per manifest ensuring repeat pruning calls are stable (no additional deletions once policy satisfied).
- Determinism Guardrails: Added end‑to‑end tests confirming identical seeds reuse runs, manifest hash equality, and equity/metrics determinism.
- Lint & Type Gates: Repository made Ruff‑clean and mypy‑clean (strict) across `src/`, `tests/`, and `scripts/`; added richer typing (TypedDict, explicit annotations) and removed legacy `typing.List/Dict/Tuple` usage.
- SSE Enhancements: Event flush + incremental stream endpoints validated; tests assert heartbeat presence, snapshot inclusion, resume semantics, ETag caching, and no duplication beyond buffer.

### Architectural Adjustments
- Dataset Registry Auto‑Registration: Benchmark script can auto-register a CSV dataset (local dev convenience) when absent, preserving determinism enforcement after registration.
- Unified Time Handling: All internal epochs normalized to ms int64 via a single pathway to eliminate scattered `pd.to_datetime` variants and ensure consistent DST behavior.
- Structured Logging Hooks: Introduced targeted structured logs around provenance fallback to support future telemetry collection (metrics/log aggregation readiness).

### Current Status Summary
System supports deterministic single-symbol backtests with full artifact set, validation summary (baseline placeholders for some tests), anomaly counters, retention trimming, and clean static analysis gates. OpenAPI contract partially exists (needs enrichment for newly surfaced fields: `data_hash`, `calendar_id`, `anomaly_counters`).

### Deferred / Pending Items
- OpenAPI Spec Enrichment: Add new response fields (`validation_summary`, `data_hash`, `calendar_id`, `anomaly_counters`) and SSE event schemas with examples.
- Metrics Expansion: Additional portfolio metrics (exposure %, turnover) documentation alignment with implementation naming.
- Validation Detail Artifacts: Flesh out block bootstrap & permutation distribution artifacts (currently summarized only).
- Configuration Hash Inputs Doc: Explicitly document which fields (and code/version salts) feed the run hash.
- Pre-commit Hook Documentation: Although lint/type are clean, doc how contributors should run or rely on pre-commit (if not yet added to repo).

### Near-Term Next Steps (Proposed)
1. Spec & OpenAPI Update: Align contracts with implemented provenance & anomaly fields.
2. Add Lightweight Metrics for Fallback Events: Counter increment (in-memory) exposed via `/health` for observability.
3. Document Time Normalization Guarantees: Separate ADR or section describing DST handling policy (ambiguous=raise default, options used, future clipping purpose).
4. Add Ingestion Regression CI Step: Ensure ingestion baseline diff runs automatically on PR (if not already wired) and fails on schema/hash drift.
5. Expand Validation: Implement at least minimal Monte Carlo slippage noise stub if not present; expose p-values in metrics summary.

---

## REST API Surface (Draft)

| Method | Path | Purpose |
|--------|------|---------|
| POST | /runs | Create/idempotent run |
| GET | /runs | List recent runs (<=100) |
| GET | /runs/{id} | Run detail + metrics summary snapshot |
| POST | /runs/{id}/cancel | Request cancellation (if running) |
| GET | /runs/{id}/events | SSE stream (see Event Types) |
| GET | /runs/{id}/artifacts | List artifact manifest |
| GET | /runs/{id}/artifact/{name} | Download specific artifact |
| GET | /candles | Fetch candle slice (chart pre-view) |
| GET | /features | On-demand feature preview (small range, non-persisted) |
| GET | /presets | List presets |
| POST | /presets | Create/update preset |
| GET | /presets/{name} | Fetch preset |
| DELETE | /presets/{name} | Delete preset |
| GET | /health | Liveness + version hash |

### Example Request: POST /runs
Request Headers: Idempotency-Key (optional), Authorization: Bearer <token>
Body:
```
{
	"symbol": "AAPL",
	"timeframe": "1h",
	"start": 1672531200000,
	"end": 1675209600000,
	"provider": "local",
	"indicators": [ { "name": "sma", "params": { "length": 20 } }, { "name": "sma", "params": { "length": 50 } } ],
	"strategy": { "name": "dual_sma", "params": { "fast": 20, "slow": 50 } },
	"risk": { "name": "fixed_fraction", "params": { "fraction": 0.25 } },
	"execution": { "commission_per_share": 0.005, "slippage_bps": 1.5, "borrow_bps": 50 },
	"validation": { "permutation": { "n": 200 }, "block_bootstrap": { "n": 200, "block_size": 24 } },
	"seed": 42
}
```
Response 201:
```
{ "run_id": "uuid", "hash": "config_hash", "status": "queued" }
```
Response 200 (idempotent replay):
```
{ "run_id": "uuid", "hash": "config_hash", "status": "running", "reused": true }
```

### Error Model
Unified JSON:
```
{ "error": { "code": "INVALID_PARAM", "message": "fast must be < slow", "details": { "field": "strategy.params.fast" }, "retryable": false } }
```
Standard codes: INVALID_PARAM, NOT_FOUND, CONFLICT, RATE_LIMITED, INTERNAL_ERROR, CANCELLED.

### Candle Fetch (GET /candles)
Query Params: symbol, timeframe, start, end, provider, limit (optional, for preview).
Response:
```
{ "symbol": "AAPL", "timeframe": "1h", "candles": [ { "ts": 1672531200000, "o": 135.2, "h": 136.0, "l": 134.9, "c": 135.7, "v": 123456 }, ... ] }
```

### Feature Preview (GET /features)
Query: symbol, timeframe, start, end, provider, indicators=JSON-encoded list.
Response merges candles + requested shifted features for quick UI overlay (not cached persistently):
```
{ "ts": [...], "close": [...], "sma_20": [...], "sma_50": [...] }
```

### SSE Events (GET /runs/{id}/events)
HTTP Response: text/event-stream
Example:
```
event: stage
data: {"run_id":"uuid","seq":3,"ts":1672531205000,"stage":"strategy"}

event: progress
data: {"run_id":"uuid","seq":4,"ts":1672531205100,"stage":"strategy","progress":0.42}

event: completed
data: {"run_id":"uuid","seq":15,"ts":1672531210000,"metrics_summary":{"total_return":0.12}}
```

## Event Stream Schema (Detailed)

Base Envelope Fields:
```
{
	run_id: STRING,
	seq: INT,          // monotonically increasing per run
	ts: BIGINT,        // epoch ms
	type: STRING,      // one of below
	stage?: STRING,    // if relevant
	progress?: FLOAT,  // 0..1 for stage-level progress
	message?: STRING,
	data?: OBJECT      // type-specific payload
}
```

Event Types & data payloads:
1. heartbeat: { uptime_ms: BIGINT }
2. stage: { stage: STRING, previous_stage?: STRING }
3. progress: { stage: STRING, progress: FLOAT }
4. warning: { code: STRING, detail?: STRING }
5. error: { code: STRING, message: STRING }
6. cancelled: { at_stage: STRING }
7. completed: { metrics_summary: MetricsSummary }
8. validation_progress (optional granular): { subtask: STRING, completed: INT, total: INT }

Resumption: Client may send Last-Event-ID header; server starts seq > given. Maintain in-memory ring buffer (size ~256) or optional persistence of last state.

## Execution & Simulation Semantics

### Position Targeting Timeline
- At bar t (using data up to t, strategy inspects shifted features representing information through t-1), risk sizing derives target_position_t.
- Order to adjust from actual_position_{t-1} to target_position_t is submitted for execution at open of bar t+1 (T+1 model).
- Last bar (N) cannot execute order (dropped) -> potential residual position flattened artificially? v1: optionally auto-flat at end using last close (config flag `auto_flatten_end`).

### Fill Price Model
Config `execution.fill_price`: 'open_next' (default) or 'mid_next' or 'vwap_next'.
If bar t+1 missing (data end) -> no fill.
Slippage: if slippage_bps provided, effective price = base_price * (1 + direction * slippage_bps/10000).
Commission: commission_per_share * |qty| (shares). If notional-based future extension.
Borrow: If position short overnight, borrow accrual per bar = (borrow_bps / 10000) * (bar_duration_year_fraction) * |position_notional|.

### Quantity Calculation
If target specified as notional fraction f of equity at bar t (pre-change equity_t), desired_notional = f * equity_t.
qty = desired_notional / price_ref.
Direction sign from signal (+1 long, -1 short, 0 flat).
Adjustment order qty_order = qty - current_position_qty.

### Partial / Invalid Fills
If volume==0 at bar t+1: either skip fill (config `skip_zero_volume=true`) or fill anyway (assuming synthetic liquidity). If skipped, position target not met; optionally reissue next bar? v1: no reissue (deterministic).

### Trade Recording
Trade record timestamp = bar t+1 ts for fills.
Store fee, slippage component, borrow cost separately.

### Equity & PnL
Mark-to-market each bar using close (or choose config `mtm_price: close|mid|last`).
Realized PnL on fills: (fill_price - avg_cost_previous) * delta_position (sign-aware). For shorts, signs handled by delta.
Unrealized PnL = (current_price - avg_cost) * position_qty.

### Drawdown
Maintain running equity peak; drawdown = equity/peak - 1. Drawdown duration resets when new peak established.

### Causality Enforcement Recap
All feature columns are shifted +1 before strategy evaluation. Strategy at bar t never sees bar t's unshifted feature values (nor bar t price except open? open accessible is still part of bar t; to avoid lookahead, treat open_t as known at start of bar t). Implementation: compute indicators on raw candles; store raw; produce shifted view used in strategy pipeline.

### End-of-Run Handling
- Auto-flatten (if enabled) generates final synthetic trade at last bar close.
- Compute residual borrow accrual for final holding up to last bar.

### Determinism Factors
Cost rounding: store doubles with no rounding except where needed; avoid floating non-determinism by using decimal context? v1: rely on IEEE 754 but ensure consistent formatting when hashing (hash excludes floating representation differences by rounding to 12 decimal places in canonical JSON).

## Validation Frameworks Design

### Permutation Test
Goal: Determine if temporal ordering of strategy signals contributes to performance beyond random rearrangements.
Method:
1. Extract per-trade returns (or per-bar PnL increments if trade-level not feasible) list R.
2. For i in 1..N (N from config): permute order (Fisher-Yates with RNG derived seed) producing R_i.
3. Compute metric of interest (total_return or Sharpe) for each R_i.
4. p_value = (#(metric_i >= metric_actual) + 1) / (N + 1) for right-tailed test.
Outputs: distribution summary percentiles.
Edge: If trade_count < 5 -> skip.

### Block Bootstrap
Goal: Preserve autocorrelation structure while resampling to form confidence intervals of returns.
Method:
1. Choose block_size B.
2. Determine required blocks K = ceil(len(R) / B).
3. For each replicate: sample K starting indices uniformly; concatenate blocks (truncate to len(R)).
4. Compute metric & collect distribution.
Outputs: chosen percentile CI.
Edge: If len(R) < B*2 -> reduce B = max(2, floor(len(R)/3)).

### Monte Carlo Trade/Slippage Noise
Goal: Assess sensitivity to execution cost randomness.
Method:
1. For each replicate: add random slippage noise ~ Normal(0, sigma_bps) to base slippage (placeholder constant sigma maybe 50% of configured slippage).
2. Recompute equity path adjusting trade realized prices; metrics.
Edge: If no trades -> skip.

### Walk-Forward (Simplified v1)
Goal: Partition dataset into sequential windows to compare in-sample vs out-of-sample performance without parameter optimization yet.
Config: windows (int) -> number of equal segments.
Method:
1. Split bar range into W sequential segments.
2. For each segment i>0 treat previous segments (0..i-1) as in-sample aggregated equity; segment i as out-sample (report metrics separately).
Outputs: list of segment returns.
Edge: If W < 2 -> skip.

### Aggregation & Output
Each selected test runs sequentially (emit validation_progress events).
Consolidate into validation_summary.json per data model spec; update metrics_summary with e.g., permutation_p_value if present.

## Artifacts & Retention Policy

### Artifact Generation Order
1. metrics.json (after metrics stage)
2. equity.parquet, drawdown.parquet, trades.parquet
3. validation_summary.json (if any validation tests)
4. summary.json (aggregate: config subset + key metrics + validation highlight)
5. plots.png (optional; generate after summary using equity & drawdown)
6. manifest.json (final step)

### summary.json Structure
```
{
	run_id: STRING,
	created_at: BIGINT,
	config_hash: STRING,
	symbol: STRING,
	timeframe: STRING,
	start: BIGINT,
	end: BIGINT,
	strategy: { name: STRING, params: OBJECT },
	metrics: { total_return: FLOAT, sharpe: FLOAT, max_drawdown: FLOAT },
	validation: { permutation_p_value?: FLOAT, block_bootstrap_return_ci?: [FLOAT,FLOAT] }
}
```

### Manifest Construction
- Initialize list after each file write computing sha256.
- When complete, write manifest, fsync, then update DB row with artifacts_manifest_sha.

### Retention Algorithm
Pseudo:
```
completed = SELECT run_id FROM runs WHERE status='completed' ORDER BY completed_at DESC OFFSET 100;
FOR each old_run in completed: delete_directory(runs/old_run); DELETE FROM runs WHERE run_id=old_run;
```
Run after each successful completion inside orchestrator (synchronous; low cost single-user).

### Integrity Verification Endpoint (Optional Future)
GET /runs/{id}/verify -> recompute hashes; returns list of mismatches.

### Naming Conventions
All artifact base names lowercase snake_case; timeseries parquet uses singular base name (equity, drawdown, trades).

## Performance, Instrumentation & Determinism Notes

Targets (heuristic v1 single-user on modern laptop):
- 1 year hourly (~6000 bars) full run (dual SMA, single symbol): < 300 ms after warm cache.
- Cold run (including data load from local file): < 1.5 s.
Levers:
1. Caching: candle + feature caches keyed by hash, skip recompute.
2. Vectorization: Use columnar operations (pandas/pyarrow in implementation) instead of per-bar Python loops except strategy callback if simple (can still vectorize crossovers).
3. Memory: Single symbol dataset small; keep frames in-memory; release intermediate raw (unshifted) feature arrays post-shift.
4. Streaming: Emit progress every 250ms or stage completion (whichever earlier) to avoid chatty SSE.
5. Hash Canonicalization: JSON dumps with sorted keys & numeric rounding (12 decimal) to ensure stable hash across floating noise.

Determinism Checklist:
- Fixed seed stored in run config; each module derives sub-seed = sha256(seed + module_name) truncated to int32.
- No wall-clock dependent logic (except timestamps of events which don't affect results).
- Cost models purely functional of inputs + config.
- Manifest built after all artifacts written to freeze state.

## Security & Single-User Constraints

Context: Single trusted user (desktop or local network) but still implement guard rails.

Auth:
- Static API token (config file env var) required in `Authorization: Bearer` header. If absent -> 401.

Rate Limiting:
- Simple in-memory leaky bucket: e.g., 10 run creations per minute (more than sufficient single-user) to avoid accidental flooding.

Path Sandboxing:
- All file operations constrained to working root; validate artifact name (whitelist set) to prevent path traversal.

Input Validation:
- Numeric bounds: fraction (0,1], lengths > 1, fast < slow for dual_sma.
- Time range sanity: start < end, max bars threshold (e.g., 250k) to avoid runaway memory.

Error Handling:
- No stack traces leaked; INTERNAL_ERROR generic plus correlation run_id; logs contain traceback.

Resource Limits:
- Memory guard: approximate footprint = bars * columns * 16 bytes; refuse if > threshold (config, e.g., 200 MB) for dataset.

Dependency Safety:
- Hash code version (git commit or manual version string) in manifest; future: verify file integrity.

## Testing Strategy Outline

### Layers
1. Unit Tests:
	- Indicator functions: correctness vs known small arrays.
	- Strategy crossover logic: known sequences produce expected signals.
	- Risk sizing: fraction sizing stable across varying equity.
	- Execution fills: T+1 semantics, cost application.
2. Property Tests (quickcheck style):
	- Indicators monotonic window length increases don't produce negative length outputs.
	- PnL accounting invariants: equity == cash + position_qty * price - fees_cum (within tolerance).
3. Scenario / Integration Tests:
	- End-to-end run with synthetic deterministic candles (linear price) verifying expected trades & metrics.
	- Cancellation mid-run stops further stages.
4. Regression Tests:
	- Golden manifest hash for canonical small run; detect unintended changes.
5. Statistical Validation Tests (lightweight):
	- Permutation test p-value distribution uniform under null synthetic strategies.

### Determinism Tests
- Re-run identical config twice -> identical metrics & manifest hashes.

### Performance Benchmarks & Instrumentation
- End-to-end harness: `scripts/bench/perf_run.py` (JSON output for CI attachment).
- Micro benchmarks: `scripts/bench/risk_slippage.py` measuring risk sizing & slippage adapter call latency.
- Coverage XML artifact produced in CI; warning budget enforced at zero (warnings -> failure).

### Error Handling Tests
- Invalid parameters return 400 with structured error.
- Missing run id -> 404.

### SSE Tests
- Connect mid-run; receive ordered events with increasing seq.
- Reconnect with Last-Event-ID returns subsequent events only.

## Proposed Directory Structure (Implementation Phase)
```
backend/
	app/
		api/
			__init__.py
			routes_runs.py
			routes_data.py
			routes_features.py
			routes_presets.py
			routes_artifacts.py
			routes_health.py
			sse.py
		core/
			config.py
			hashing.py
			errors.py
			logging.py
			events.py
			retention.py
		data/
			providers/
				base.py
				provider_local.py
			candles.py
			calendar.py
			cache.py
		features/
			registry.py
			indicators/
				sma.py
		strategy/
			base.py
			dual_sma.py
		risk/
			sizing_base.py
			fixed_fraction.py
		execution/
			simulator.py
			cost_models.py
		metrics/
			metrics.py
		validation/
			permutation.py
			block_bootstrap.py
			monte_carlo.py
			wfo.py
		orchestrator/
			runner.py
			state_machine.py
		artifacts/
			writer.py
			manifest.py
		presets/
			store.py
		persistence/
			db.py
			schemas.sql
	tests/
		unit/
		integration/
		data/
	scripts/
		init_db.py
	requirements.txt (later)
	README.md
contracts/
	openapi.yaml
```

## Requirements Coverage Mapping

| Requirement | Covered Section |
|-------------|-----------------|
| Data Layer (providers, calendars, TZ, adjustments) | Architecture Module 1; Data Model candle_cache |
| Feature/Indicator Registry (+1 bar causal shift) | Architecture Module 2; Execution Semantics (Causality) |
| Strategy Framework (base + Dual SMA) | Architecture Module 3; Directory structure (strategy/) |
| Risk Sizing (fixed fraction; hooks vol-targeting) | Module 4; Risk sizing description |
| Execution Simulator (T+1 fills, costs) | Module 5; Execution & Simulation Semantics |
| Metrics (PnL, equity, drawdown, turnover, exposure, Sharpe/Sortino) | Module 6; Metrics Summary schema |
| Validation (permutation, block bootstrap, WFO, Monte Carlo) | Module 7; Validation Frameworks Design |
| Backtest Orchestrator | Module 8; State Machine Stages |
| Runs API (CRUD + idempotency) | Module 9; REST API Surface |
| Event Stream (SSE heartbeats/progress) | Module 10; Event Stream Schema |
| Artifacts (summary.json, equity, plots, manifest) | Module 11; Artifacts & Retention |
| Presets & Retention (last 100 runs) | Module 12; Retention Algorithm |
| Determinism & Reproducibility | Performance & Determinism Notes |
| Security (single-user constraints) | Security & Single-User Constraints |
| Testing Strategy | Testing Strategy Outline |
| Directory Structure | Proposed Directory Structure |




### Listing Runs (GET /runs)
Response:
```
{ "runs": [ { "run_id":"uuid","status":"completed","hash":"...","created_at":...,"metrics_summary":{"total_return":0.12,"sharpe":1.4} } ] }
```

### Artifact Retrieval
GET /runs/{id}/artifacts -> manifest JSON.
GET /runs/{id}/artifact/equity.parquet -> binary stream (Content-Type: application/vnd.apache.parquet).

### Preset Management
POST /presets body = RunConfig-like (excluding seed optional). Upsert semantics.

### Health
GET /health -> { "status": "ok", "version": "git_sha_or_semver" }
