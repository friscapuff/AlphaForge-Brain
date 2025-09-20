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
11. Artifacts (summary, metrics, equity, drawdown, trades, validation, manifest, optional plot)
12. Presets & Retention (named configs + keep last 100 runs)

## Non-Goals (v1)
- Multi-symbol portfolios
- Live trading / order routing
- Optimization search loops
- Advanced execution microstructure modeling

## Data Contracts
Defined in detail in `data-model.md`. Key items: RunConfig, MetricsSummary, Trade, PortfolioBar (optional), ArtifactManifest, Event envelope.

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
Deterministic manifest with SHA-256 for each file. Retain newest 100 completed runs; older runs fully removed (metadata + directory).

## Determinism Guarantees
Config + code version + seed -> stable run hash. Re-running yields identical artifacts (hash stable) barring code changes or external data differences. Submodule seeds derived from root seed.

## Performance Targets
## Performance & Instrumentation Targets
Cached small run < 300 ms, cold < 1.5 s (validated via `scripts/bench/perf_run.py`).
Supplemental micro benchmarks (`scripts/bench/risk_slippage.py`) report per-call latency (risk:* & slippage:* keys) to catch regressions.
CI attaches coverage XML artifact; warning budget enforced at zero.

## Security & Constraints
Single user; static token; sandboxed file operations; size & bar count guards; no sensitive stack traces in responses.

## Testing Strategy
Unit, property, scenario, regression (manifest hash), SSE reliability, determinism re-run equivalence, validation statistical sanity.

## OpenAPI Spec
To be populated in `contracts/openapi.yaml` outlining components (schemas) and paths reflecting above endpoints.

## Future Extension Hooks
Multi-symbol, portfolio hedging, advanced execution, optimization loops, external storage integration.

---
See `plan.md` for expanded operational detail and `data-model.md` for precise schema definitions.

