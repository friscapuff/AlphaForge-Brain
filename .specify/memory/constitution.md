<!--
Merged Constitution: Incorporates legacy realism/schema rigor with new Project A backend lab orientation.
-->

# Constitution: Project A (Backend Trading Lab)

Version: 3.0.0 | Ratified: 2025-09-19 | Last Amended: 2025-09-19

## I. Purpose

This system exists as a **private, single-user backend trading lab** focused on simulating, testing, and analyzing trading strategies. The ultimate goal of Project A is to deliver a robust backend foundation that supports data ingestion, strategy execution, backtesting, risk analysis, and persistence. Project B, the future frontend/UI layer, will consume these backend services — Project A’s responsibility is to provide the APIs, modules, and infrastructure that make that possible.

## II. Core Principles

1. **Backend-Centric**: Project A delivers all core functionality as backend services and APIs. Project B (frontend) is not implemented here, only prepared for.
2. **Separation of Concerns**: Backend handles computation, persistence, and simulation logic. Frontend will only visualize and interact via APIs.
3. **Single User Simplicity**: No authentication, profiles, or RBAC. Secrets only apply to external providers (e.g., market data API keys).
4. **Modular Growth**: Indicators, strategies, metrics, and risk modules can be added incrementally with minimal coupling.
5. **Reproducibility**: Runs and results are stored with their configurations, ensuring experiments can be replayed.
6. **Lean Foundations**: Focus is on achieving a manageable, maintainable backend first, then extending into UI via Project B.
7. **Extensibility**: Backend architecture allows new strategies, indicators, and metrics to be added easily.
8. **Realism & Integrity**: Retain essential realism tenets (calendars, costs, no lookahead) proportionate to v1 scope.
9. **Determinism**: Hash-based idempotent runs; stable seeds and manifest hashing.

## III. Environments

* **Staging (Backend)**: Primary environment where all APIs, strategy runs, simulations, and persistence occur. User interaction is via backend services (to be consumed by Project B).
* **Research**: Internal backend-only mode for testing algorithms or modules. Invisible to the end user.
* **Production**: Explicitly out of scope for Project A.

## IV. Core Modules

1. **Data Ingestion**: Historical and real-time market data, normalized into consistent formats.
2. **Indicator Engine**: A modular library of technical indicators, filters, and DSP-based tools (including Ehlers methods).
3. **Strategy Engine**: Rule-based trading strategies defined by combining indicators and conditions.
4. **Backtest & Simulation Engine**: Historical execution with parameters for commission, slippage, and spreads.
5. **Risk & Metrics**: Performance statistics, equity curves, drawdowns, expectancy, and risk-adjusted returns.
6. **Persistence Layer**: Saving/loading of strategies, configurations, and run artifacts.
7. **Experiment Management**: Handling of runs, duplication rules, and idempotency.
8. **Observability Layer**: Logging, heartbeat updates, error reporting, and run status.
9. **API Layer**: FastAPI endpoints exposing all backend functionality for eventual consumption by Project B (UI).

## V. Technology Choices

* **Backend**: Python + FastAPI, with Pandas/NumPy for data handling.
* **Indicators**: TA-Lib and custom modules (e.g., Ehlers DSP methods).
* **Database**: SQLite for local runs, with migration path to Postgres.
* **Communication**: JSON APIs with Server-Sent Events (SSE) for live updates.
* **Deployment**: Local environment first, with optional containerization (Docker) for portability.
* **Frontend (Future, Project B)**: Mentioned only as consumer of APIs; no implementation in Project A.

## VI. User Experience (via Backend)

* APIs allow creation of strategies, indicator configs, and runs.
* Backtests and simulations are executed via backend services.
* Results (equity curves, trade lists, performance metrics) are exposed via API.
* Project B will later consume these APIs and present them visually.

## VII. Data & Retention

* Retain last 100 runs by default.
* Runs and results stored locally in SQLite + filesystem.
* Oldest runs pruned automatically, with manual export for long-term retention.
* Artifacts hashed (SHA256) and checksummed for integrity.

## VIII. Observability

* Structured logs for backend processes.
* Progress and errors streamed via SSE.
* Heartbeat updates every 5 seconds for active runs.
* Failures clearly flagged, with distinction between full and partial outputs.

## IX. Governance

* System evolves via local code updates and version control (git).
* No external approvals or waivers required.
* Schema and module changes versioned with notes.
* Backward compatibility maintained wherever possible.

## X. Guiding Vision

Project A aims to provide a **backend foundation** for a staging-only lab where strategies, indicators, and simulations can be built, tested, and persisted. It is deliberately backend-only: no frontend is built here. Instead, APIs and infrastructure are prepared so Project B can later deliver the full UI experience on top of this solid base.

---
## Appendix A: Legacy Foundational Standards (Carried Forward)

These summarize critical elements from the prior ecosystem constitution that remain in force, adapted to single-user scope:

### A1. Realism Essentials
- Use exchange calendars; avoid lookahead; model basic costs (commission, spread, borrow) and T+1 fills.
- Explicit handling of missing data (gap flags) and corporate actions (adjust or document if out-of-scope temporarily).

### A2. Schema-as-Contract Lite
- JSON response/request models versioned implicitly via OpenAPI (future explicit schema IDs optional).
- Breaking field changes require run hash version bump and doc note.

### A3. Determinism & Reproducibility
- Config + seed + code version -> run hash; artifacts manifest hashed.
- Non-deterministic sources (random sampling in validation) seeded deterministically.

### A4. Testing Discipline
- Unit tests for cost math, indicator shift, run hash stability.
- Property tests for permutation p-value bounds, bootstrap CI monotonicity with N.
- Determinism test: identical config -> identical manifest hashes.

### A5. Observability
- Structured JSON logs keyed by run_id.
- SSE event envelope: {run_id, seq, ts, type, ...}.

### A6. Secrets Handling
- Only external provider keys; no user auth secrets. Stored in environment, never committed.

### A7. Change Management
- Version (semantic) bump in constitution when contract-affecting changes made; note added to CHANGELOG (future).

---
## Amendment Process

Minor: documentation or clarifications (no version bump).  
Patch: internal refactors not altering external contract (increment patch).  
Minor Version: additive backwards-compatible API/module.  
Major Version: removal/rename/breaking semantics.
