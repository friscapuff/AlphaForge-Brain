# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.1.0/) and this project adheres (prospectively) to Semantic Versioning.

## [0.3.1-dev] - 2025-09-23
### Added
- Guarantee: When querying Run Detail with `?include_anomalies=true`, `summary.anomaly_counters` is now always present (empty object if no counters) and documented in OpenAPI.
- Regression guard tests for `to_epoch_ms` covering multi-row localization and explicit DST ambiguous/nonexistent handling (baseline case + dedicated DST tests added).
- Deterministic testing infrastructure: `freeze_time` fixture (subclasses `datetime` inside project modules) for exact timestamp assertions in manifest & SSE tests.
- Central `random_seed_fixture` eliminating scattered ad-hoc seeding for permutation / bootstrap invariants.
- Parameterized walk-forward segmentation unit tests covering multiple stride/warmup combinations plus insufficient-total edge case.
- README Section 7.a documenting deterministic testing infrastructure and contributor guidelines.
- README Section 7.b "Robustness & Validation" detailing statistical validation guarantees & usage pattern.
- OpenAPI additive diff contract test (`tests/contract/test_openapi_diff.py`) with snapshot for future additive-only evolution.
- Snapshot placeholder (`openapi_snapshot.json`) to be expanded incrementally as endpoints stabilize (initial minimal schema ensures new paths reported as additive).
- Planned replay verification script placeholder task (T075) tracked; upcoming `scripts/verify_replay.py` will perform dual-run hash & artifact hash assertion.

### Changed
- Walk-forward segmentation test now derives expected segment counts algorithmically instead of brittle hard-coded numbers.
- Tasks spec updated with rationale table for new infrastructure.
- API overview annotated with timestamp determinism addendum.

### Fixed
- Removed prior brittle timestamp prefix assertions; now full equality under frozen time ensuring zero flake baseline.

### Internal
- Test factories expanded to guarantee timezone-aware datetime defaults across models.
 - Task spec Phase 3.9 partially advanced: T069-T071 completed (quickstart updated, README robustness section added, OpenAPI diff test in place).


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
