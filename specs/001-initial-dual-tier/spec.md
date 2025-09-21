# Project A Backend – Consolidated Specification (v1)

This document consolidates the execution plan, data model, and interface surface for the single-user Studio backtesting + validation engine. It is the authoritative high-level spec; implementation details live in `plan.md` and `data-model.md`.

## Scope
Provide REST + SSE services enabling a UI to configure and launch deterministic backtests from chart state and retrieve metrics, artifacts, and live progress. Single symbol, single strategy (dual SMA example) baseline with validation utilities and retention.

## Functional Overview
Pipeline: load candles -> compute shifted indicators -> generate strategy signals -> risk sizing -> T+1 execution simulation w/ costs -> metrics -> optional validation -> artifact emission -> retention trimming.

## Supported Modules (v1)
1. Data Layer (candle normalization, calendar, caching)
2. Feature/Indicator Registry (+1 bar causal shift enforced)
3. Strategy Framework (base + dual SMA example)
4. Risk Sizing (fixed fraction, volatility_target, kelly_fraction)
5. Execution Simulator (T+1 fills, commissions, slippage, borrow, pluggable slippage adapters: spread_pct, participation_rate)
6. Metrics (return, Sharpe, Sortino, drawdowns, turnover, exposure, trade stats)
7. Validation (permutation, block bootstrap, Monte Carlo slippage noise, simplified walk-forward)
8. Backtest Orchestrator (stage machine + events)
9. Runs API (idempotent create/list/detail/cancel)
10. Event Stream (SSE with stage/progress/heartbeat; legacy flush + long-lived incremental streaming endpoint, ETag/after_id caching)
11. Artifacts (summary, metrics, equity, drawdown, trades, validation, manifest, optional plot, provenance fields)
12. Presets & Retention (named configs + keep last 100 runs, idempotent pruning)
13. Timestamp Normalization Utility (single authoritative path for all epoch ms conversions)

## Non-Goals (v1)
- Multi-symbol portfolios
- Live trading / order routing
- Optimization search loops
- Advanced execution microstructure modeling

## Data Contracts
Defined in detail in `data-model.md`. Key items: RunConfig, MetricsSummary, Trade, PortfolioBar (optional), ArtifactManifest, Event envelope.

Additional surfaced fields (implemented):
- Run Detail: `data_hash`, `calendar_id`, `validation_summary` (alias `validation`), optional `summary.anomaly_counters` when `include_anomalies=true`.
- Validation Summary: includes `anomaly_counters` mapping (e.g., `unexpected_gaps`, `duplicates_dropped`).
- Manifest Provenance: guaranteed fallback `data_hash`/`calendar_id` even if upstream metadata acquisition fails (logged via structured event `writer.provenance.fallback`).

## API Surface (Summary)
- POST /runs (idempotent)
- GET /runs, GET /runs/{id}, POST /runs/{id}/cancel
- GET /runs/{id}/events (SSE flush; supports after_id + ETag caching)
- GET /runs/{id}/events/stream (long-lived incremental SSE)
- GET /runs/{id}/artifacts, GET /runs/{id}/artifact/{name}
- GET /candles (preview)
- GET /features (on-demand feature preview)
- Presets: GET/POST/GET by name/DELETE
- GET /health

Auth: Static bearer token. Errors: unified JSON with code/message.

## Execution Semantics (Summary)
Signals at bar t become orders executed at bar t+1 (open or configured fill price). Final bar optionally auto-flatten. Costs applied deterministically. Features strictly shifted to avoid lookahead.

## Validation (Summary)
Optional tests produce p-values / confidence intervals; results integrated into validation_summary.json and surfaced in metrics summary where relevant.

## Artifacts & Retention
Deterministic manifest with SHA-256 for each file. Retain newest 100 completed runs; older runs fully removed (metadata + directory). Retention implementation is idempotent: repeated pruning calls after enforcement return the same removal set (stable state map keyed by manifest identity).

Provenance Fallback: On failure to obtain dataset metadata, writer synthesizes a provenance record (hash of synthetic content and default calendar) and logs a structured warning; downstream consumers always see populated fields.

## Determinism Guarantees
Config + code version + seed -> stable run hash. Re-running yields identical artifacts (hash stable) barring code changes or external data differences. Submodule seeds derived from root seed. Ingestion benchmarking plus baseline diff tooling enforce row count + data hash stability across refactors.

## Performance & Instrumentation Targets
Cached small run < 300 ms, cold < 1.5 s (validated via ingestion performance benchmark `scripts/bench/ingestion_perf.py`).
Baseline ingestion JSON diff (`scripts/bench/ingestion_baseline_diff.py`) fails CI when row counts or data hash drift (elapsed time reported but not gating).
Potential micro benchmarks (future): risk sizing & execution cost adapters; current focus on end-to-end ingestion determinism.
CI attaches coverage XML; Ruff + mypy must pass clean (0 warnings/errors) as quality gate.

## Security & Constraints
Single user; static token; sandboxed file operations; size & bar count guards; no sensitive stack traces in responses.

## Testing Strategy
Unit, property, scenario, regression (manifest hash), SSE reliability, determinism re-run equivalence, validation statistical sanity, anomaly counter presence, provenance fallback logging, timestamp normalization edge (DST ambiguous/nonexistent, NaT preservation, future clip) tests.

## OpenAPI Spec
To be populated in `contracts/openapi.yaml` outlining components (schemas) and paths reflecting above endpoints.

## Future Extension Hooks
Multi-symbol, portfolio hedging, advanced execution, optimization loops, external storage integration.

## Time Handling Policy
All internal timestamps represented as epoch milliseconds (int64). A centralized utility `to_epoch_ms` applies the following rules:
- Naive strings interpreted as UTC unless `assume_tz` provided.
- DST ambiguous times raise by default; caller may pass `ambiguous=False` to choose first occurrence.
- Non-existent local times (spring forward) may be shifted forward (`nonexistent="shift_forward"`).
- NaT values preserved as <NA> in resulting Int64 series.
- Optional `clip_future` drops future timestamps relative to current UTC.
This eliminates scattered ad hoc `pd.to_datetime` calls and ensures consistent gap / anomaly detection.

## Anomaly Counters
Ingestion & validation paths surface anomaly counts (e.g., `unexpected_gaps`, `duplicates_dropped`) aggregated and exposed through validation summary and optionally run detail (`include_anomalies=true`). These provide early warning signals for data integrity issues without failing runs by default.

---
See `plan.md` for expanded operational detail and `data-model.md` for precise schema definitions.

