<!--
Merged Constitution: Incorporates legacy realism/schema rigor with new AlphaForge Brain backend lab orientation.
-->

# Constitution: AlphaForge Brain (Backend Trading Lab)

Version: 3.1.0 | Ratified: 2025-09-19 | Last Amended: 2025-09-20

## I. Purpose

This system exists as a **private, single-user backend trading lab** focused on simulating, testing, and analyzing trading strategies. The ultimate goal of AlphaForge Brain is to deliver a robust backend foundation that supports data ingestion, strategy execution, backtesting, risk analysis, reproducibility, and artifact integrity. A future frontend/UI layer (external to this repository) will consume these backend services — AlphaForge Brain’s responsibility is to provide the APIs, deterministic modules, streaming channels, and infrastructure that make that possible.

## II. Core Principles

1. **Backend-Centric**: AlphaForge Brain delivers all core functionality as backend services and APIs. A future UI is not implemented here, only prepared for.
2. **Separation of Concerns**: Backend handles computation, persistence, and simulation logic. Frontend will only visualize and interact via APIs.
3. **Single User Simplicity**: No authentication, profiles, or RBAC. Secrets only apply to external providers (e.g., market data API keys).
4. **Modular Growth**: Indicators, strategies, metrics, and risk modules can be added incrementally with minimal coupling.
5. **Reproducibility**: Runs and results are stored with their configurations, ensuring experiments can be replayed.
6. **Lean Foundations**: Focus is on a maintainable core (data → features → strategy → risk → execution → metrics → validation → artifacts) before any external UI.
7. **Extensibility**: Backend architecture allows new strategies, indicators, metrics, risk, slippage, and validation methods to be added easily.
8. **Realism & Integrity**: Retain essential realism tenets (calendars, costs, no lookahead) proportionate to scope; avoid premature microstructure modeling.
9. **Determinism**: Hash-based idempotent runs; stable seeds and manifest hashing (with integrity chain links).

## III. Environments

* **Staging (Backend)**: Primary environment where all APIs, strategy runs, simulations, and persistence occur. User interaction is via backend services (to be consumed by an external future UI).
* **Research**: Internal backend-only mode for experimenting with algorithms or modules.
* **Production**: Explicitly out of scope (no multi-user SLA commitments).

## IV. Core Modules

1. **Data Ingestion**: Local provider + caching (CSV/Parquet). External live feeds out-of-scope initially.
2. **Indicator Engine**: Modular technical indicators (Dual SMA initial) with registry for incremental expansion.
3. **Strategy Engine**: Rule-based strategies combining indicator outputs (initial: dual_sma) via a runner.
4. **Execution Simulator**: T+1 fills, zero-volume handling, commission & slippage modeling, pluggable slippage adapters.
5. **Risk & Metrics**: Position sizing (fixed_fraction, volatility_target, kelly_fraction), equity & performance metrics.
6. **Validation & Statistical Tests**: Permutation, bootstrap, Monte Carlo, walk-forward partitions with deterministic seeding.
7. **Artifacts & Manifest**: Metrics, trades, validation merged into integrity-hashed manifest (with chain linkage `chain_prev`).
8. **Experiment Management**: Run creation, idempotent hashing, retention pruning, preset persistence (JSON/SQLite hybrid).
9. **Observability Layer**: Structured logging, incremental event buffering, streaming & flush endpoints.
10. **API Layer**: FastAPI REST + SSE (flush & long-lived streaming) for downstream UI consumption.

## V. Technology Choices

* **Backend**: Python + FastAPI, with Pandas/NumPy for data handling.
* **Indicators**: Internal registry (extensible). External TA-Lib integration deferred.
* **Database**: SQLite for local runs, with potential migration path to Postgres.
* **Communication**: JSON REST APIs + SSE (one-shot flush + long-lived incremental streaming with optional heartbeat).
* **Deployment**: Local execution + optional containerization (Docker) for portability.
* **Frontend (Future)**: External consumer of the API; not implemented here.

## VI. User Experience (via Backend)

* APIs allow creation of run configurations (strategy, risk, execution, validation).
* Backtests and simulations executed via orchestrated pipeline (data → features → strategy → risk → execution → metrics → validation → artifacts).
* Results (equity curves, trade lists, performance metrics, validation summaries) are exposed via API & artifacts.
* Presets support quick reuse of canonical configurations.

## VII. Data & Retention

* Retain last 100 runs by default (configurable later).
* Runs and results stored locally in SQLite + filesystem.
* Oldest runs pruned automatically; manual export permitted before pruning.
* Artifact manifest hashed (SHA256) with chained integrity (`chain_prev`).

## VIII. Observability

* Structured logs for backend processes.
* Progress and errors streamed via SSE (flush + streaming endpoints).
* Heartbeat events during idle streaming intervals (default ~15s) until terminal event.
* Failures clearly flagged; partial vs terminal status distinguished.
* ETag-based event flush caching to reduce payload redundancy.

## IX. Governance

* System evolves via local code updates and version control.
* No external approvals required; single-user stewardship.
* Schema & module changes recorded in CHANGELOG + semantic versioning.
* Backward compatibility favored; breaking changes deferred unless essential.

## X. Guiding Vision

AlphaForge Brain provides a **deterministic backend foundation** where strategies, indicators, risk models, and simulations can be built, tested, benchmarked, and persisted. It is deliberately backend-only: no frontend is built here. Instead, APIs (REST + SSE), artifacts, and contracts are prepared so an external UI can later deliver a richer user experience atop this stable core.

---
## Appendix A: Legacy Foundational Standards (Carried Forward)

These summarize critical elements from the prior ecosystem constitution that remain in force, adapted to single-user scope:

### A1. Realism Essentials
- Use exchange calendars where relevant; avoid lookahead; model basic costs (commission, slippage, spread) and T+1 fills.
- Explicit handling / documentation of missing data; corporate actions may be documented or deferred.

### A2. Schema-as-Contract
- OpenAPI is the source of truth; additive fields allowed (minor bump). Removing/renaming is breaking (major bump) and must be documented.
- Risk/slippage model enums and SSE endpoints are core contract surfaces.

### A3. Determinism & Reproducibility
- Canonical JSON of config + seed + code version -> run hash.
- Artifact manifest hashed with integrity chain (`chain_prev`).
- Validation stochastic elements seeded deterministically (per-run offset seeds).
- No hidden randomness in execution, risk, or slippage models.

### A4. Testing Discipline & Quality Gates
- Unit + integration tests for indicators, strategy, execution edge cases, metrics, validation, SSE streaming & resume.
- Determinism equivalence test: identical config -> identical manifest hashes.
- Risk & slippage model behavior tests (monotonic and scaling assertions).
- Zero warnings policy (warnings treated as errors in CI).
- Type safety: mypy strict (0 errors baseline enforced).
- Lint & formatting: ruff (no outstanding findings, format check required).

### A5. Observability
- Structured JSON logs keyed by run_id.
- Event buffer assigns stable incremental IDs; SSE flush uses ETag `<run_hash>:<last_event_id>` for caching.
- Streaming endpoint replays backlog then tails new events; heartbeats maintain client liveness.

### A6. Secrets Handling
- Only external provider keys; no user auth secrets. Stored in environment, never committed.

### A7. Change Management
- Semantic versioning: MAJOR (breaking), MINOR (additive feature), PATCH (internal / docs / fixes).
- This amendment elevates constitution version to 3.1.0 reflecting additive streaming + caching + risk/slippage + manifest chain enhancements.
- CHANGELOG synchronized with release tags (e.g., v0.2.1).

---
## Amendment Process

Minor: documentation or clarifications (no version bump).  
Patch: internal refactors not altering external contract (increment patch).  
Minor Version: additive backwards-compatible API/module.  
Major Version: removal/rename/breaking semantics.
