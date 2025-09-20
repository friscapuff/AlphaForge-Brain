# Tasks – Project A Backend (Initial Dual Tier Feature)

This actionable roadmap derives from `plan.md`, `data-model.md`, `spec.md`, `research.md`, `contracts/openapi.yaml`, and `quickstart.md`.

Conventions:
- Task IDs: T### (sequential)
- [P] = Can run in parallel with other [P] tasks (different files / isolated concern)
- No mark = must follow dependencies (same file or upstream contract)
- Each task outcome is a PR-ready, test-validated unit
- Use FastAPI + Pydantic v2, Python 3.11, SQLite, pure filesystem

Phasing Overview:
1. Foundation & Tooling
2. Core Domain Models & Registries
3. Data & Feature Pipeline
4. Strategy, Risk, Execution
5. Metrics & Validation
6. Orchestrator & Runs Lifecycle
7. API Endpoints & Contracts
8. Artifacts & Retention
9. SSE Events & Cancellation
10. Presets & Integrity
11. Testing Matrix & Determinism Harness
12. Packaging, Docs, Polish

---
## Phase 1 – Foundation & Tooling

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T001 | Initialize project structure (src layout: domain/, api/, infra/, tests/, scripts/) | directories + `pyproject.toml`, `.python-version` | none |
| [x] | T002 | Base tooling config (ruff, mypy, pytest, pre-commit, editorconfig) | `.ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml` | T001 |
| [x] | T003 | Settings module (env parsing, constants) [P] | `infra/config.py` | T001 |
| [x] | T004 | Logging setup (structured JSON logger) [P] | `infra/logging.py` | T001 |
| [x] | T005 | Hashing + time helpers [P] | `infra/utils/hash.py`, `infra/utils/time.py` | T001 |
| [x] | T006 | SQLite DB bootstrap | `infra/db.py`, `infra/migrations/001_init.sql` | T001 |
| [x] | T007 | Domain errors + error envelope mapper | `domain/errors.py`, `api/error_handlers.py` | T001 |
| [x] | T008 | FastAPI app skeleton + health route | `api/app.py`, `api/routes/health.py` | T002,T004 |

Parallel Set 1 Example:
- T003, T004, T005 can execute concurrently after T001.

---
## Phase 2 – Core Domain Models & Registries

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T009 | Pydantic schemas: RunConfig, IndicatorSpec, StrategySpec, RiskSpec, ExecutionSpec, ValidationSpec | `domain/schemas/run_config.py` | T005 |
| [x] | T010 | Metrics summary & artifact manifest schemas | `domain/schemas/metrics.py`, `domain/schemas/artifacts.py` | T009 |
| [x] | T011 | Indicator registry (decorator + metadata struct) | `domain/indicators/registry.py` | T009 |
| [x] | T012 | Strategy registry + base interface | `domain/strategy/base.py` | T009 |
| [x] | T013 | Risk sizing registry + interface | `domain/risk/base.py` | T009 |
| [x] | T014 | Validation test registry skeleton | `domain/validation/registry.py` | T009 |
| [x] | T015 | Dual SMA indicator implementation | `domain/indicators/sma.py` | T011 |
| [x] | T016 | Dual SMA strategy implementation | `domain/strategy/dual_sma.py` | T012,T015 |

Parallel Set 2 Example:
- T011, T012, T013, T014 in parallel after T009.

---
## Phase 3 – Data & Feature Pipeline

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T017 | Candle loader abstraction + provider registry | `domain/data/providers/base.py`, `domain/data/registry.py` | T009,T006 |
| [x] | T018 | Local provider implementation (CSV/Parquet) | `domain/data/providers/local.py` | T017 |
| [x] | T019 | Candle caching layer (hashing, parquet) | `infra/cache/candles.py` | T017,T005 |
| [x] | T020 | Feature computation engine | `domain/features/engine.py` | T011,T019 |
| [x] | T021 | Feature caching layer | `infra/cache/features.py` | T020,T005 |
| [x] | T022 | Data slice API function | `domain/data/slice.py` | T019 |

Parallel Set 3 Example:
- T019 and T020 partially parallel after T017 once indicator metadata available.

---
## Phase 4 – Strategy, Risk, Execution

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T023 | Signal timeline generator | `domain/strategy/runner.py` | T016,T020 |
| [x] | T024 | Risk sizing engine (fixed fraction) | `domain/risk/engine.py` | T013,T023 |
| [x] | T025 | Execution simulator (T+1 fills, costs) | `domain/execution/simulator.py` | T024,T009 |
| [x] | T026 | Trade & portfolio state structures | `domain/execution/state.py` | T025 |
| [x] | T027 | Edge case handling (zero-volume, flatten end) | `domain/execution/simulator.py` | T025 |

---
## Phase 5 – Metrics & Validation

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T028 | Metrics calculator (returns, sharpe, drawdown) | `domain/metrics/calculator.py` | T026 |
| [x] | T029 | Validation permutation test | `domain/validation/permutation.py` | T014,T028 |
| [x] | T030 | Validation block bootstrap | `domain/validation/block_bootstrap.py` | T014,T028 |
| [x] | T031 | Validation Monte Carlo slippage | `domain/validation/monte_carlo.py` | T014,T028 |
| [x] | T032 | Walk-forward partition reporting | `domain/validation/walk_forward.py` | T014,T028 |
| [x] | T033 | Aggregate validation runner | `domain/validation/runner.py` | T029-T032 |

Parallel Set 4 Example:
- T029–T032 in parallel after T028.

---
## Phase 6 – Orchestrator & Runs Lifecycle

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T034 | Run state machine (progress, cancel checks) | `domain/run/orchestrator.py` | T025,T028,T033,T021 |
| [x] | T035 | Idempotent run creation service (hash reuse) | `domain/run/create.py` | T009,T034,T006,T005 |
| [x] | T036 | Retention pruning service (keep 100) | `domain/run/retention.py` | T035 |
| [x] | T037 | Manifest builder & artifact writer | `domain/artifacts/writer.py` | T028,T026 |
| [x] | T038 | Validation artifact integration | `domain/artifacts/validation_merge.py` | T037,T033 |
| [x] | T039 | Final manifest finalize + integrity hashing | `domain/artifacts/manifest.py` | T037,T038,T005 |

---
## Phase 7 – API Endpoints & Contracts

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T040 | Error handler wiring (exceptions -> envelope) | `api/error_handlers.py` | T007,T008 |
| [x] | T041 | /health endpoint (version, status) | `api/routes/health.py` | T008 |
| [x] | T042 | /runs POST (idempotent create) | `api/routes/runs_create.py` | T035,T040 |
| [x] | T043 | /runs list endpoint | `api/routes/runs_list.py` | T035 |
| [x] | T044 | /runs detail endpoint | `api/routes/runs_detail.py` | T035,T039 |
| [x] | T045 | /runs cancel endpoint | `api/routes/runs_cancel.py` | T034 |
| [x] | T046 | /runs artifacts endpoints | `api/routes/runs_artifacts.py` | T039 |
| [x] | T047 | /candles preview endpoint | `api/routes/candles.py` | T022 |
| [x] | T048 | /features preview endpoint | `api/routes/features.py` | T020 |
| [x] | T049 | /presets CRUD endpoints | `api/routes/presets.py` | T009,T006,T005 |
| [x] | T050 | OpenAPI enrichment (examples, errors) | `contracts/openapi.yaml` | T042-T049 |

---
## Phase 8 – Events & Cancellation

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T051 | One-shot SSE event flush endpoint (buffered deterministic events) | `api/routes/run_events.py` | T034 |
| [x] | T052 | In-memory ordered event buffer (stable ids, reuse on identical run hash) | `domain/run/event_buffer.py` | T051 |
| [x] | T053 | Cancellation integration (emit cancelled) | `domain/run/orchestrator.py` | T034,T045 |

---
## Phase 9 – Artifacts & Retention Finalization

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T054 | Artifact hashing & manifest integrity tests | `tests/artifacts/test_manifest.py` | T039 |
| [x] | T055 | Retention pruning integration test | `tests/runs/test_retention.py` | T036 |
| [x] | T056 | Validation summary merge test | `tests/validation/test_merge.py` | T038 |

---
## Phase 10 – Presets & Integrity

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T057 | Preset persistence service (DB + JSON) | `domain/presets/service.py` | T006,T009 |
| [x] | T058 | Presets endpoints tests | `tests/presets/test_presets_api.py` | T049,T057 |
| [x] | T059 | Idempotency hash reuse test | `tests/runs/test_idempotency.py` | T042,T035 |

Implementation Notes (T057–T058):
- Persistence Strategy: The service first checks `ALPHAFORGE_PRESET_PATH`; if set, all presets are stored as a single JSON object mapping `preset_id -> record` at that path (facilitates atomic test isolation). Otherwise a `presets/` directory is used with one file per preset (`<id>.json`).
- Deterministic ID: `preset_id = sha256(canonical{"name","config"})[:16]` ensures identical (name, config) pairs re-use the same id (idempotent create semantics).
- Create Semantics: Duplicate POST with identical payload returns 200 and the same preset_id (no 409) to simplify stateless UI retries.
- Deletion: Removes in-memory cache entry and rewrites single file or leaves other per-file JSON documents untouched.
- Listing Order: Sorted ascending by `created_at` for stable pagination; tests filter by returned id to avoid interference from any preloaded defaults.
- Test Isolation: Each test sets `ALPHAFORGE_PRESET_PATH` to a temp file; dependency-injected service re-initializes when the path changes.


---
## Phase 11 – Testing Matrix & Determinism Harness

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T060 | Unit tests: indicators & strategy | `tests/indicators/test_sma.py`, `tests/strategy/test_dual_sma.py` | T015,T016 |
| [x] | T061 | Execution simulator edge tests | `tests/execution/test_simulator.py` | T027 |
| [x] | T062 | Metrics calculator tests | `tests/metrics/test_calculator.py` | T028 |
| [x] | T063 | Validation tests suite | `tests/validation/test_validation_suite.py` | T033 |
| [x] | T064 | SSE stream integration test | `tests/sse/test_events.py` | T051,T052 |
| [x] | T065 | End-to-end run scenario test | `tests/e2e/test_full_run.py` | T042-T046,T039 |
| [x] | T066 | Determinism re-run equivalence test | `tests/e2e/test_determinism.py` | T065,T059 |
| [x] | T067 | Error model tests | `tests/api/test_errors.py` | T040,T042 |

---
## Phase 12 – Packaging, Docs, Polish

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T068 | Performance microbench script | `scripts/bench/perf_run.py` | T065 |
| [x] | T069 | API docs refinement & examples | `contracts/openapi.yaml` | T050 |
| [x] | T070 | README + Quickstart integration | `README.md` | T065,T069 |
| [x] | T071 | Dockerfile + container entrypoint | `Dockerfile`, `docker-entrypoint.sh` | T008,T050 |
| [x] | T072 | CI pipeline config & pre-commit enable | `.github/workflows/ci.yml` | T002,T060-T067 |
| [x] | T073 | Final lint/type pass & mypy strict adjustments | Reports only | T060-T072 |

---
## Phase 13 – Recently Added & Backlog Enhancements

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T074 | Manifest integrity chaining (`chain_prev`) | `domain/artifacts/manifest.py`, manifests updated | T039 |
| [x] | T075 | SQLite-backed preset index option (env switch) | `domain/presets/service.py` | T057 |
| [x] | T076 | Additional risk models (volatility_target, kelly_fraction) | `domain/risk/engine.py`, tests at `tests/risk/test_new_risk_models.py` | T013,T024 |
| [x] | T077 | Slippage adapters (spread_pct, participation_rate) | `domain/execution/simulator.py`, tests at `tests/execution/test_slippage_models.py` | T025 |
| [x] | T078 | True incremental SSE streaming (long-lived, optional heartbeats) | `api/routes/run_events.py` | T051 |
| [x] | T079 | ETag / If-None-Match support for event flush caching | `api/routes/run_events.py` | T051 |

---
## Phase 14 – Release Instrumentation & Reporting

| Done | ID | Task | Deliverable / Files | Dependencies |
|------|----|------|---------------------|--------------|
| [x] | T080 | Add CHANGELOG and version bump 0.2.0 | `CHANGELOG.md`, `pyproject.toml` | T073 |
| [x] | T081 | CI coverage reporting artifact | `.github/workflows/ci.yml` | T072 |
| [x] | T082 | Benchmark isolate risk & slippage micro timings | `scripts/bench/risk_slippage.py` | T068,T076,T077 |
| [x] | T083 | README badges (coverage, version, license) | `README.md` | T080,T081 |
| [x] | T084 | Spec & plan doc refresh for new models | `spec.md`, `plan.md` | T076,T077,T080 |

Implementation Notes (T068):
- Harness: `scripts/bench/perf_run.py` executes warm-up iterations then times end-to-end run creation (orchestrator + metrics + validation) with deterministic seeds.
- Config: Minimal dual_sma config (fast=5, slow=20) over 1-day synthetic timeframe (`2024-01-01` to `2024-01-02`, timeframe `1m`).
- Output: Prints JSON with mean, median, p95 (approx via max for small sample), min, max, trade_count_mean, and sample hashes; supports `--output` file write.
- Reproducibility: Injects `src/` into `sys.path` for standalone execution outside pytest; uses fixed seeds per iteration offset.
- Cleanup: Removes artifacts between iterations unless `--keep-artifacts` specified.
- Makefile: Added `bench` target (runs 1 warm-up + 5 iterations by default).

Implementation Notes (T069–T070):
Implementation Notes (T078–T079):
Implementation Notes (T082–T084):
- `risk_slippage.py` microbenchmark measures per-call latency for risk models (fixed_fraction, volatility_target, kelly_fraction) and slippage adapters (none, spread_pct, participation_rate) using synthetic deterministic frame. Outputs JSON keyed by `risk:<model>` & `slippage:<model>`.
- README badges updated (coverage placeholder, benchmarks) and added risk_slippage usage section.
- Spec & plan updated to include new slippage adapters, incremental SSE streaming endpoint, ETag caching, and benchmark instrumentation references.

- Added long-lived incremental SSE endpoint: `GET /runs/{run_hash}/events/stream` which supports resume via `Last-Event-ID`, emits buffered historical events first, then periodic heartbeat events every ~15s while awaiting new events. Terminates after terminal status once all events delivered.
- Legacy flush endpoint `/runs/{run_hash}/events` enhanced with `after_id` query filter and ETag caching: ETag format `<run_hash>:<last_event_id>`. If client supplies `If-None-Match` and no new events, returns 304 with empty body.
- Backwards compatibility: existing tests using `Last-Event-ID` header still function; header still honored when `after_id` not provided.
- OpenAPI updated to document new endpoint, query/header parameters, and ETag semantics.
- OpenAPI updated: corrected presets schema (preset_id, items), simplified create semantics (single 200 idempotent), added minimal dual SMA preset example, clarified delete response.
- README expanded: presets workflow (create/list/get/delete), microbenchmark usage, validation artifacts mention, features list updated to include presets + benchmark harness.
- Alignment: Preset endpoints now reflect runtime route shapes; removed outdated provider/commission field names in examples (execution fee -> fee_bps, risk model field).

---
## Parallel Execution Guidance
Examples (invoke agents or scripts referencing task IDs):
```
# After T001
run-task T003 & run-task T004 & run-task T005

# After T009
parallel-run T011 T012 T013 T014

# After T028
parallel-run T029 T030 T031 T032

# Validation & SSE focus (after core path ready)
parallel-run T051 T057
```

---
## Dependency Summary
- Config + hashing utilities (T003-T005) underpin caching, idempotency, manifest (T019,T021,T035,T039).
- Feature engine (T020) precedes strategy runner (T023) and ultimately execution (T025) and metrics (T028).
- Validation runner (T033) integrates before artifacts finalize (T039) so summary present.
- Orchestrator (T034) central; cancellation (T045,T053) and SSE (T051-T052) layer on it.

## Acceptance Criteria Trace
Mapping core requirements to tasks:
- Determinism & Idempotency: T005, T009, T035, T059, T066
- Causal Shift & Indicators: T011, T015, T020, T060
- T+1 Execution & Costs: T025, T027, T061
- Metrics Suite: T028, T062
- Validation Methods: T029-T033, T063
- Progress Events (SSE Flush): T051-T052, T064
- Manifest Chain Integrity: T074
- SQLite Presets Option: T075
- Artifacts & Manifest Hashing: T037-T039, T054, T065
- Retention Policy: T036, T055
- Presets: T057-T058
- Cancellation: T045, T053
- Error Model: T007, T040, T067
- Performance Target: T068
- Documentation: T069, T070
- Packaging & Tooling: T001-T002, T071-T072, T073

## Next Step
Core feature set, validation suite, presets, performance harness, documentation refresh, Docker packaging, and CI pipeline are complete (T001–T072). Remaining delivery step in this phase is final strictness & reproducibility polish (T073).

Immediate Focus:
1. T073 – Final lint/type strict pass (COMPLETED):
	- (DONE) mypy strict: all modules pass with zero errors; unused ignores removed; generics & precise types added.
	- (DONE) Run tests with warnings-as-errors; baseline established (0 warnings).
	- (DONE) Ruff format + lint: zero findings locally; matches CI gate.
	- (DONE) README reproducibility addendum (payload + seed replay procedure) added.
	- (DONE) Warning budget report (0) at `scripts/reports/warning_budget.json`.
	- (DONE) Local container build & characterization: image raw size 250,609,242 bytes (~239–250 MB depending on reporting); python:3.11-slim base + scientific stack (numpy, pandas, scipy, pyarrow, statsmodels). Cold start to Uvicorn ready ~2–3s on dev hardware (import bound).

Status Note (T073): All strictness objectives achieved (types, lint, warnings=0, reproducibility docs, container sanity). Ready to proceed to backlog items (T076–T079) or new enhancements.

Implementation Notes (T076–T077):
- Risk Models:
	- volatility_target: Scales base_fraction by (target_vol / realized_vol) using rolling stdev of pct_change with lookback window; early bars (insufficient history) receive effectively zero sizing via large sentinel volatility. Clamped to max fraction 1.0.
	- kelly_fraction: Applies dampened Kelly formula f = p - (1-p)/R, then multiplies by base_fraction for prudence and clamps to [0,1]. Both integrate through unified apply_risk switch in `domain/risk/engine.py`.
	- Tests verify monotonic scaling (later lower realized vol -> >= position size) and sensitivity to probability/payoff changes.
- Slippage Adapters:
	- spread_pct: Adjusts execution price by half the configured fractional spread in direction of trade before bps slippage/fees.
	- participation_rate: Impact proportional to (order_qty / bar_volume) * participation_pct, capped at 100% participation; applied multiplicatively to price pre-costs.
	- Both integrated via `_apply_slippage_model` in `domain/execution/simulator.py` executed prior to bps slippage & fees pipeline. Tests assert price impact presence and monotonicity with order size.
	- OpenAPI updated: risk.model enum extended; execution.slippage_model documented with model-specific param blocks.
	- Determinism: No added randomness; relies solely on provided DataFrame values ensuring reproducible fills.

T073 Command Checklist (reference):
```
# 1. Type & lint
poetry run mypy src
poetry run ruff check .
poetry run ruff format --check .

# 2. Tests w/ warnings enforced
PYTHONWARNINGS=error::UserWarning poetry run pytest -q --disable-warnings

# 3. Local container build (optional validation)
docker build -t alphaforge-backend:dev .
docker run --rm -p 8000:8000 alphaforge-backend:dev

# 4. Reproducibility doc snippet generator (future optional)
python scripts/env/gen_repro_doc.py  # (if implemented later)
```

Environment Readiness Note:
- Local system virtualization + WSL2 enablement completed; Docker build path validated by presence of `Dockerfile` and entrypoint script (T071) and CI config (T072). Proceed with optional local image build to sanity-check runtime size & startup time during T073.

Post-Phase Opportunities (next focus candidates):
- True long-lived incremental SSE (T078) if UI requires push vs poll.
- ETag-based caching (T079) for event flush to reduce payloads.
- Additional risk & slippage models (T076,T077) for broader strategy coverage.
- Performance profiling around validation scaling (possible T080 future).

### Reproducibility Checklist (T073 Final)
- Pin Python minor version (pyproject + CI uses 3.11.x) – DONE
- Enforce lock presence & integrity (`scripts/env/check_env.py --strict`) – DONE
- Deterministic seeds per run (config.seed + derived offsets) – DONE
- Stable hashing (canonical JSON) for run idempotency – DONE
- Manifest integrity chain (`chain_prev`) – DONE
- No warnings policy (CI treats warnings as errors) – DONE (0 warning baseline)
- Formatting enforced (ruff format --check) – DONE
- Time freezing in tests (freezegun) ensures stable timestamps – DONE
- Document poll-based SSE determinism – DONE (quickstart)
- README run reproduction section (payload + seed) – DONE
