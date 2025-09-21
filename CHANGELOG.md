# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.1.0/) and this project adheres (prospectively) to Semantic Versioning.

## [0.3.0] - 2025-09-21
### Added
- Multi-symbol data abstraction & registry (Phase J G01-G08) enabling future portfolio expansion without breaking existing contracts.
- Strict typing hardening: mypy --strict across src + tests with zero errors (G11-G13).
- Typing modernization (PEP 604 unions, builtin generics) and removal of legacy typing imports (G14).
- Additional mypy warning gates (`warn-unused-ignores`, `warn-redundant-casts`) enforced (G15).
- Expanded Ruff ruleset (bugbear, pyupgrade strict, additional error detection) fully remediated (G16).
- CI mypy snapshot gate & diff report artifacts (`.mypy_snapshot_src.json`, `mypy_diff.md`) (G17, G19).
- Pre-commit selective mypy hook for changed files accelerating local feedback (G18).
- Typing + lint timing benchmark (`timing_report.py`) with JSON/Markdown outputs establishing performance budget (G21).
- Documentation: README "Typing & Lint Guarantees" and architecture updates reflecting abstraction and determinism enhancements (G20).

### Changed
- Manifest enriched with symbol/timeframe fields and dataset-binding hash semantics clarified (G06-G07).
- Orchestrator fully removed synthetic candle fallback; always real dataset slice for determinism (G01).
- Improved error messaging for missing symbol/timeframe (G10).

### Removed
- All stale `# type: ignore` directives (final audit left zero ignores) (G22).

### Tooling / CI
- Added mypy diff regression detection step failing build on new errors.
- Added ruff + mypy timing artifact publication for longitudinal performance tracking.

### Security / Determinism
- Strengthened run hash inclusion of dataset snapshot binding; prevents accidental cross-symbol artifact reuse.

## [0.2.2] - 2025-09-21
### Added
- SSE snapshot event now surfaces `validation_summary` and legacy alias `validation` for parity with RunDetail endpoint.

### Changed
- Test suite aligned NVDA run configs to canonical daily timeframe (`1d`) matching integrated dataset loader.

### Fixed
- Provenance fallback logging now guarantees visibility by emitting a best‑effort stdout line when structlog capture is absent.
- Failing SSE anomaly summary test due to missing validation summary field in snapshot events.

### Internal
- Added dataset file placement under `./data` during local test execution for deterministic ingestion.

### Added
- Long-lived incremental SSE streaming endpoint `/runs/{run_hash}/events/stream` with heartbeat + resume (T078).
- ETag + `after_id` incremental caching for flush endpoint `/runs/{run_hash}/events` (T079).
- Risk & slippage microbenchmark script `scripts/bench/risk_slippage.py` (T082).
- README badges (version, license, python, coverage placeholder, benchmarks) and microbenchmark docs (T083).
- Spec & plan documentation refresh covering new risk models, slippage adapters, SSE streaming & caching (T084).
- Project constitution v1.1.0 establishing 10 core principles (deterministic reproducibility, additive contracts, test-first, data integrity & provenance, modular architecture, observability & explainability, performance guardrail, pragmatic extensibility, single sources of truth, automation as policy) plus constraints & governance.

### Changed
- SSE tests hardened to ignore timestamp drift and prevent hang via early-exit fast-path for synchronous runs.
- README reorganized microbenchmark section (perf_run + risk_slippage) and clarified coverage artifact wording.

### Fixed
- Hanging SSE test due to long heartbeat interval; introduced short sleep (50ms) until terminal detection.
- Minor quoting lint issues in SSE test assertions (ruff Q000).

### Performance
- Provided per-model micro timings for risk sizing and slippage to establish regression baselines.

### Tooling / CI
- No CI config changes yet; groundwork laid for optional future benchmark regression gating using JSON outputs.

### Documentation
- Expanded spec.md & plan.md to note pluggable slippage adapters (spread_pct, participation_rate) and streaming/caching event model.
- README updated with Core Principles Summary referencing constitution.

## [0.2.1] - 2025-09-20
## [0.2.0] - 2025-09-20
### Added
- New risk sizing models: `volatility_target` and `kelly_fraction` (T076) with accompanying unit tests (`tests/risk/test_new_risk_models.py`).
- Slippage adapters: `spread_pct` and `participation_rate` (T077) integrated into execution simulator with tests (`tests/execution/test_slippage_models.py`).
- Manifest chain integrity via `chain_prev` field (T074).
- Optional SQLite-backed preset index (T075) controlled by environment switch.
- Performance microbenchmark harness (`scripts/bench/perf_run.py`) producing JSON metrics (T068).
- Warning budget report (`scripts/reports/warning_budget.json`) capturing zero‑warning baseline (T073).
- Virtualization / WSL / Docker readiness diagnostic script (`scripts/env/check_virtualization.ps1`).

### Changed
- Comprehensive strictness pass: mypy strict mode enabled across all modules; unused ignores removed; precise typing added (T073).
- Lint pipeline hardened: ruff formatting + lint enforced in CI with zero findings (T073).
- OpenAPI contract updated for new risk & slippage model enums and execution spec fields.
- README reproducibility section expanded (deterministic seeds, hashing & replay instructions).
- Execution simulator extended to apply slippage models prior to bps slippage & fees with corrected end-of-run flatten handling.

### Fixed
- Indentation logic issue in execution simulator after slippage integration (corrected flatten behavior).
- Normalized dual SMA parameter handling ensuring consistent feature column synthesis for tests.
- Eliminated pandas future/deprecation warnings (established zero‑warning test baseline).

### Performance
- Ensured cached small run latency meets target (<300ms) and documented container cold start characteristics.
- Bench harness offers early regression detection for orchestrated run timing.

### Tooling / CI
- CI treats warnings as errors; type check, lint, format, and benchmark stages separated.
- Reproducibility improvements: Python 3.11 pinned, dependency lock integrity verification script executed in pipeline.

### Security / Determinism
- Stable hashing maintained with canonical JSON serialization (sorted keys + numeric rounding) reaffirmed during strictness pass.
- Added manifest chain integrity to detect tampering or partial deletion over time.

## [0.1.0] - 2025-09-??
### Added
- Initial deterministic single-user backtest engine: data loading, indicator registry (+1 bar shift), dual SMA strategy, fixed fraction risk sizing, T+1 execution simulator with commissions/slippage/borrow, metrics suite, validation framework (permutation, block bootstrap, Monte Carlo slippage noise, simplified walk-forward), artifacts & manifest, presets, retention policy, SSE event streaming, idempotent runs API, Docker packaging, and documentation.

[0.2.0]: https://example.com/compare/v0.1.0...v0.2.0
