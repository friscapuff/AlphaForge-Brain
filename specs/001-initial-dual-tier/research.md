# Phase 0 Research – Project A Backend

## Inputs Considered
- Feature Spec: `spec.md` (single-user deterministic backtest & validation engine).
- Execution Plan: `plan.md` (detailed modules & semantics).
- Constitution v3.0.0 (backend-only lab, determinism, realism essentials, retention policy).
- User stack directives (Python 3.11, FastAPI, Pydantic v2, pandas/numpy, future Polars slot, SQLite + FS, BackgroundTasks, SSE, Poetry/uv, ruff, mypy, pytest, pre-commit, Dockerfile).
- Foundational scaffold list (16 foundation items: repo layout, config, data layer, features, strategy, risk, execution, metrics, validation, orchestrator, runs API, events SSE, artifacts, presets, tests, packaging).

## Problem Statement
Provide an idempotent backtesting service producing reproducible artifacts (metrics, equity path, trades, validation stats) from a parameterized request describing symbol/timeframe, indicator configs, strategy params, and risk/execution settings. Must stream progress, enforce causal feature shift (+1 bar), simulate T+1 execution with costs, and maintain only the last 100 runs.

## Key Challenges & Considerations
| Area | Challenge | Approach |
|------|-----------|----------|
| Determinism | Stable artifact hashes with floating ops | Canonical JSON rounding + manifest hashing |
| Causality | Avoid lookahead in indicator availability | Registry auto-shift + enforcement guard tests |
| Performance | <300ms warm run | Cache candles/features; vectorize indicators & strategy |
| Validation | Statistical tests reproducible | Seed derivation per module (root_seed + module) |
| Execution | T+1 fills + costs while simple | Configurable fill model + cost functions modular |
| Extensibility | Add new indicators/strategies | Decorator-based registries (feature, strategy, metric) |
| Retention | Auto prune oldest >100 | Transactional prune after run completion |
| SSE Reliability | Resume after disconnect | Maintain in-memory ring + last seq; Last-Event-ID support |
| Idempotency | POST /runs same config returns existing | Config hash (sorted JSON) + Idempotency-Key header |

## Comparative Notes
- Typical open-source backtest libs (Backtrader, zipline) lack built-in SSE and run-level artifact manifest hashing; this system adds web-native concerns.
- Using FastAPI + BackgroundTasks suffices v1; Celery abstraction deferred (interface boundary in orchestrator).

## Data Model Emphasis
- RunConfig minimal single-symbol, extendable later to multi-symbol by turning symbol into list and adding portfolio allocation fields.
- Trade ledger normalized; portfolio bars optional but derive equity & drawdown.
- Validation outputs aggregated to a single JSON summary for quick UI consumption.

## Risk & Execution Simplifications (Deliberate v1)
- No partial volume constraint beyond optional zero-volume skip.
- Borrow cost linear approximation; no tiered financing.
- Spread & slippage bps constant; future adaptive model placeholder.

## Open Questions / Deferred
1. Multi-provider data merging (deferred, single provider per run).
2. Corporate action pipeline beyond simple adjustment flag (documented placeholder).
3. Parameter optimization grid / WFO with re-fitting (v2+).
4. Real-time incremental updates (would require websocket; SSE sufficient for batch runs now).

## Acceptance Heuristics (Phase Output)
- Research identifies clear challenges & solutions aligning with constitution.
- No contradictions with constitutional realism or determinism items.
- Provides rationale for chosen simplifications & deferrals.

## Ready-to-Implement Signals
- Risks enumerated with mitigation.
- Hashing, retention, SSE replay mechanics planned.
- Minimal v1 feature/strategy sets defined (SMA variants, Dual SMA).
