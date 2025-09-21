# AlphaForge Brain – Deterministic Single-User Trading Lab Backend

![Version](https://img.shields.io/badge/version-0.2.1-blue.svg) ![Python](https://img.shields.io/badge/python-3.11.x-blue.svg) ![Coverage](https://img.shields.io/badge/coverage-available%20in%20CI-lightgrey.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Benchmarks](https://img.shields.io/badge/bench-risk_slippage%20&%20perf_run-informational.svg)

AlphaForge Brain is a deterministic, modular backend for running strategy backtests, risk-adjusted simulations, and statistical validations. It targets a single power user who wants **repeatable experiments**, **artifact integrity**, and **low-friction iteration** without premature multi-user overhead. A future UI (out of scope here) will sit on top of these APIs.

---
## 1. Executive Overview
AlphaForge Brain executes an orchestrated pipeline: load candles → compute indicators/features → derive strategy signals → size positions (risk models) → simulate fills (slippage, fees, T+1) → compute metrics → perform validation (permutation, bootstrap, Monte Carlo, walk-forward) → assemble artifacts → emit ordered events (SSE) → persist manifest with integrity hash + chain linkage. Every run is **idempotent**: submitting the same canonical configuration returns the same `run_hash` and reuses existing artifacts.

**Why it exists:** To provide a trustworthy sandbox for researching and iterating on systematic strategies with strict reproducibility and transparent state transitions. It favors correctness, clarity, and traceable transformations over opaque monolith logic.

---
## 1.a Core Principles Summary (See full constitution: `.specify/memory/constitution.md`)
| # | Principle | Summary |
|---|-----------|---------|
| 1 | Deterministic Reproducibility | Same config + dataset snapshot → identical hash & artifacts; nondeterminism isolated or recorded. |
| 2 | Additive Contracts | Public schemas evolve additively; breaking changes require major version proposal. |
| 3 | Test-First Discipline | Failing tests precede implementation; all gates (mypy, ruff, pytest, spectral) must pass. |
| 4 | Data Integrity & Provenance | Validation summary + anomaly counters + data_hash surfaced; no silent imputation. |
| 5 | Modular Domain Architecture | Clear bounded contexts (data, features, strategy, risk, execution, validation, run). |
| 6 | Observability & Explainability | Structured logs + events enable post-hoc reasoning for every trade & anomaly. |
| 7 | Performance Guardrail | Measure first; optimize only with baseline + delta evidence. |
| 8 | Pragmatic Extensibility | Prepare only for upcoming multi-symbol/provider needs when non-breaking; avoid speculative layers. |
| 9 | Single Sources of Truth | One authoritative module per canonical dataset, registry, manifest hashing pipeline. |
| 10 | Automation as Policy | CI enforces all gates; manual checklists replaced by scripts. |

These principles drive design decisions, code review criteria, and release gating. Any deviation requires an explicit, time-bound exception documented in PR rationale.

---
## 2. Core Value Principles
| Principle | Meaning | Implementation Hooks |
|-----------|---------|----------------------|
| Determinism | Same input → same output (hash & artifacts) | Canonical JSON hashing, seeded validation, pure data transforms |
| Integrity | Artifacts tamper-evident | `manifest.json` + `manifest_hash` + `chain_prev` |
| Modularity | Swap / extend components easily | Registries (indicator, strategy, risk, slippage) |
| Observability | Understand progress & status | Ordered event buffer + SSE (flush & streaming) |
| Reproducibility | Full rerun without guessing | Config payload stored + lockfile + seed |
| Performance Insight | Measure, don’t assume | Microbenchmarks (`perf_run`, `risk_slippage`) |
| Safety & Clarity | No hidden randomness / side effects | Explicit seeds, no global mutable singletons (beyond controlled caches) |

---
## 3. High-Level Architecture
```
                +--------------------+
                |   Run Submission   |
                | (POST /runs)       |
                +---------+----------+
                          |
                    Hash & Idempotency
                          |
                  +-------v--------+
                  |  Orchestrator  |
                  +---+---+---+----+
                      |   |   |
        Data Layer <--+   |   +--> Event Buffer (ordered)
                      |   |         ^
      Feature / Indicators |         | SSE Flush / Stream
                      |   |         |
                 Strategy Runner     |
                      |             |
                  Risk Engine        |
                      |             |
               Execution Simulator   |
                      |             |
                   Metrics Calc      |
                      |             |
                  Validation Suite   |
                      |             |
                  Artifact Writer ---+
                      |
                 Manifest (hashed)
```
The orchestrator is a state machine that drives each stage deterministically. Each stage produces structured outputs that later phases consume, minimizing hidden coupling.

---
## 4. Full End-to-End Data Flow (Narrative Guide)
This section is your always-current mental model. Every run moves through the following exact phases. Each bullet contains 2–4 sentences to reinforce understanding.

1. Submission & Hashing: A client sends a `RunConfig` payload to `POST /runs`. The system canonicalizes (stable key ordering, normalized types) and hashes it with metadata (code version, seed). If a previous run with the same hash exists, the existing artifacts are reused and no recalculation occurs. This enables stateless retries and instant cache hits for deterministic experimentation.
2. Candle Loading & Caching: The data provider (currently local CSV/Parquet) loads the candle range, normalizes schema (timestamp, open/high/low/close/volume), and stores a cached Parquet slice keyed by its content hash. Subsequent identical data requests avoid re-loading overhead. Data immutability ensures downstream determinism.
3. Indicator & Feature Computation: Indicators (e.g., dual SMA) are computed over the candle frame with explicit lookback windows and no forward fill that causes lookahead bias. Features are cached similarly, keyed by both raw data hash and indicator parameters. This layer produces a feature matrix consumed by strategies.
4. Strategy Signal Generation: The strategy runner aligns indicator values and produces discrete position or signal states (e.g., long/flat toggles when fast/slow SMA cross). It deliberately avoids sizing decisions, producing only intent. This isolation allows reuse of signals across multiple risk model experiments.
5. Risk Sizing: Risk engine converts signals into position sizes via the selected model (`fixed_fraction`, `volatility_target`, `kelly_fraction`). Each implementation clamps output and uses stable historical statistics (e.g., realized volatility) for scaling. The result is a position series (desired target size per bar) ready for execution simulation.
6. Execution Simulation: The simulator walks through bars applying T+1 fills (signal at bar N executed at bar N+1 open or chosen price proxy). Slippage models (none, `spread_pct`, `participation_rate`) and fee/slippage basis points adjust fill prices deterministically. Edge cases like zero volume or end-of-range flattening are handled explicitly to avoid orphaned state.
7. Trade & State Tracking: As fills occur, trades are instantiated, and portfolio state (cash, position, equity curve) is updated. The engine ensures chronological consistency and prevents impossible negative fill conditions. Intermediate states are not mutated retroactively, preserving auditability.
8. Metrics Computation: Returns, drawdowns, Sharpe-like ratio, and other summary statistics derive from the equity curve and trade list. All metrics functions are pure: they accept immutable structures and return new aggregates. This encourages independent revalidation or extension.
9. Validation Suite: Statistical modules (permutation, bootstrap, Monte Carlo, walk-forward) run using deterministic seeds derived from the base seed plus indexed offsets. Outputs (p-values, confidence intervals, partition summaries) become structured validation artifacts. This phase does not alter prior artifacts—only appends results.
10. Artifact Assembly & Manifest: The artifact writer compiles metrics, trades, validation outputs, and run configuration references. A `manifest.json` with `manifest_hash` plus `chain_prev` (linking to the prior run’s manifest hash) provides integrity chaining. Any tampering or partial deletion becomes detectable when reconstructing the chain.
11. Event Buffering & Emission: Each phase emits events (e.g., `started`, `data_loaded`, `features_ready`, `strategy_done`, `risk_done`, `execution_done`, `metrics_done`, `validation_done`, `artifacts_finalized`, `completed`). These are stored in an ordered in-memory buffer with stable incremental IDs. Clients either poll via flush endpoint (with `ETag` caching) or attach a long-lived streaming SSE connection for incremental push.
12. Completion & Reuse: Once the terminal event is emitted, the run enters a stable state. Re-submitting identical configuration yields the same hash and returns immediately referencing existing artifacts (no recomputation). This drastically shortens iterative parameter tuning cycles.

### ASCII Sequence (Abbreviated)
```
Client -> API (/runs) -> Orchestrator
Orchestrator -> Data Provider -> Cache
Orchestrator -> Indicator Engine -> Feature Cache
Orchestrator -> Strategy Runner
Orchestrator -> Risk Engine
Orchestrator -> Execution Simulator
Orchestrator -> Metrics Calculator
Orchestrator -> Validation Suite
Orchestrator -> Artifact Writer -> Manifest
Orchestrator -> Event Buffer -> (SSE Stream / Flush)
Client <- SSE: progress ... terminal
```

---
## 5. Domain Components
### Indicators
Each indicator registers via a decorator into the indicator registry. Parameters are validated and serialized for caching keys. Adding a new indicator requires a pure function returning a pandas Series/DataFrame aligned to input index.

### Strategies
Strategies transform aligned indicator outputs into target exposure signals. They do not execute trades or size positions. This keeps them testable and cheap to iterate.

### Risk Models
Risk models translate exposure intent into position sizing. `volatility_target` scales the base fraction inversely with realized volatility; `kelly_fraction` applies a conservative Kelly sizing formula dampened by a base fraction. All models clamp sizes to valid ranges and are side-effect free.

### Slippage Models
Slippage adapters transform theoretical execution price before costs: `spread_pct` shifts by half-spread; `participation_rate` applies impact proportional to order participation in bar volume. They run before fee and generic BPS slippage adjustment, keeping ordering explicit and auditable.

### Execution Simulator
Applies T+1 logic, zero-volume guards, and produces trade records and state deltas. Determinism is maintained by avoiding random partial fills or latency modeling in this scope.

### Metrics & Validation
Metrics compute time-series and aggregate performance figures. Validation modules assess robustness: permutation tests re-randomize signal structure; bootstrap resamples segments; Monte Carlo perturbs distributions; walk-forward splits evaluate temporal generalization.

### Artifacts & Manifest
Artifacts (metrics, trades, validation summaries) are written to disk. A manifest consolidates pointers, sizes, and hashes. `chain_prev` links prior manifest to build a verifiable lineage.

---
## 6. Events & Streaming
Two modes:
1. Flush Endpoint: `GET /runs/{run_hash}/events` returns all events (optionally filtered with `after_id`). ETag header `<run_hash>:<last_event_id>` allows 304 responses if no new events.
2. Streaming Endpoint: `GET /runs/{run_hash}/events/stream` replays backlog then waits for new events, sending periodic heartbeat events (~15s) until terminal.

Event Schema (conceptual):
```json
{
  "run_hash": "string",
  "id": 7,
  "ts": "2025-09-20T12:34:56.789Z",
  "type": "metrics_done",
  "payload": {"metrics": {"sharpe": 1.23}}
}
```
Clients can recover from disconnect by supplying `Last-Event-ID` (stream) or `after_id` (flush).

---
## 7. Determinism & Reproducibility
Determinism rests on canonical configuration serialization, stable seeded flows, and absence of nondeterministic IO. Run hash = SHA-256 over canonical JSON (sorted keys, normalized types) plus version metadata. Validation modules derive sub-seeds from the base seed using indexed offsets (ensuring independence yet reproducibility). Manifest chaining allows verifying no retroactive mutation across historical runs.

Reproduce Checklist:
1. Same code & `poetry.lock`.
2. Original JSON payload (include `seed`).
3. Same environment variables (if any feature flags introduced later).
4. Submit via `/runs`; identical `run_hash` indicates reuse.
5. Fetch artifacts; verify manifest hash & `chain_prev` alignment.

---
## 8. Risk & Slippage Model Usage
Example risk config (volatility target):
```json
"risk": {"model": "volatility_target", "params": {"base_fraction": 0.2, "target_vol": 0.15, "lookback": 30}}
```
Kelly variant:
```json
"risk": {"model": "kelly_fraction", "params": {"base_fraction": 0.1, "win_prob": 0.55, "reward_risk": 1.4}}
```
Slippage example:
```json
"execution": {"slippage_model": "participation_rate", "params": {"participation_pct": 0.1}, "slippage_bps": 4, "fee_bps": 1.2}
```

---
## 9. API Guide (Practical Quickstart)
| Action | Endpoint | Method | Notes |
|--------|----------|--------|-------|
| Create run | `/runs` | POST | Returns `run_hash` (idempotent) |
| List runs | `/runs` | GET | Sorted recent (retention window) |
| Run detail | `/runs/{run_hash}` | GET | Includes status & manifest link |
| Artifacts | `/runs/{run_hash}/artifacts` | GET | Manifest, metrics, validation references |
| Events (flush) | `/runs/{run_hash}/events` | GET | ETag + `after_id` support |
| Events (stream) | `/runs/{run_hash}/events/stream` | GET | SSE incremental |
| Presets CRUD | `/presets` | POST/GET/DELETE | Idempotent create by (name, config) |

Minimal run creation (PowerShell):
```powershell
$body = '{
  "symbol": "TEST", "timeframe": "1m", "start": "2024-01-01", "end": "2024-01-02",
  "indicators": [{"name":"sma","params":{"window":5}},{"name":"sma","params":{"window":15}}],
  "strategy": {"name":"dual_sma","params":{"fast":5,"slow":15}},
  "risk": {"model":"fixed_fraction","params":{"fraction":0.1}},
  "execution": {"slippage_bps":0,"fee_bps":0},
  "validation": {"permutation": {"trials": 3}},
  "seed": 42
}'
Invoke-RestMethod -Method POST -Uri http://localhost:8000/runs -ContentType 'application/json' -Body $body
```

---
## 10. Presets Workflow
Presets wrap frequently used configurations. Creating identical (name, config) returns the existing `preset_id` (no duplication or conflict errors). Backed by JSON file or SQLite index depending on environment variable selection. This optimizes iterative UI flows where a user tweaks only one parameter between runs.

---
## 11. Benchmarks & Performance Instrumentation
Two complementary harnesses:
- End-to-End (`scripts/bench/perf_run.py`): Measures orchestration latency, trade counts, summary stats.
- Micro (`scripts/bench/risk_slippage.py`): Isolates per-model call overhead for risk sizing & slippage transforms.

Run examples:
```powershell
poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1
poetry run python scripts/bench/risk_slippage.py --iterations 300 --risk-models fixed_fraction,volatility_target,kelly_fraction --slippage none,spread_pct,participation_rate
```

---
## 12. Repository Layout
```
src/
  api/                # FastAPI app & routes
  domain/             # Core domain logic (strategy, risk, execution, validation, artifacts)
  infra/              # Config, logging, db, utilities
scripts/
  bench/              # Performance & microbench harnesses
  dev/                # Developer helpers
specs/                # Architecture, plan, openapi, research
presets/              # Stored presets (if not overridden)
```

---
## 12.a NVDA Dataset Placement (Group 1 Foundation)
For the NVDA 5‑Year integration feature the ingestion layer expects a canonical CSV file at:

```
./data/NVDA_5y.csv
```

Required columns (case-sensitive):
`timestamp,open,high,low,close,volume` (optional: `adj_close` ignored)

Normalization assumptions:
- Source timezone: America/New_York (converted to UTC epoch ms `ts`)
- Daily timeframe; gaps classified via exchange-calendars (NYSE schedule proxy)
- Duplicate timestamps: keep first, drop rest (counter incremented)
- Missing critical fields: row dropped
- Zero volume: retained with `zero_volume=1`
- Future dated rows (ts > now UTC): dropped

Deterministic dataset hash (`data_hash`) is computed over canonical columns:
`ts,open,high,low,close,volume,zero_volume` with stable float formatting and ordering.

If you need a different location, set up or symlink `data/` accordingly before running Group 2+ tasks.


---
## 13. Extensibility Guide
### Add an Indicator
1. Implement a pure function returning a pandas Series.
2. Decorate with the registry decorator specifying name & parameter schema.
3. Add unit test ensuring no lookahead (shift checks) and window correctness.

### Add a Strategy
1. Define parameter schema.
2. Consume indicator outputs → produce discrete signal states (e.g., -1/0/1 or boolean transitions).
3. Test over a small synthetic frame with deterministic expectations.

### Add a Risk Model
1. Implement sizing function taking position intent and price history (if needed).
2. Enforce clamping & deterministic math (no random draws).
3. Register in risk engine switch; add tests for monotonic scaling.

### Add a Slippage Adapter
1. Accept trade direction, quantity, bar volume/price context.
2. Produce adjusted price; keep side-effect free.
3. Register & test impact vs baseline.

### Add Validation Method
1. Accept deterministic seeds; derive sub-seeds from base.
2. Return structured result schema (summary + any detail arrays).
3. Add reproducibility test ensuring identical outputs with same config.

---
## 14. Local Development & Quality Gates
Install & Run:
```powershell
poetry install --with dev
poetry run uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```
Quality Gates:
```powershell
poetry run pytest --disable-warnings -q
poetry run mypy src
poetry run ruff check .
```
Zero warnings are tolerated (CI treats warnings as errors). Type & lint gates must be green before merging changes.

Dev Script Helper:
```powershell
pwsh scripts/dev/run_api.ps1 -Port 8000 -Reload
```

---
## 15. Troubleshooting & FAQ
| Symptom | Cause | Resolution |
|---------|-------|-----------|
| Docker build slow | Cold dependency layer | Re-run; subsequent builds leverage cache layers |
| Re-run not recomputing | Idempotent hash hit | Change a config field (e.g., seed) to force recompute |
| Streaming idle | No new events | Heartbeats every ~15s confirm liveness |
| Different hash after pull | Dependency drift | Reinstall with lockfile; ensure no uncommitted changes |
| Validation timing large | High trials count | Reduce `permutation.trials` or bootstrap sample size |

Virtualization Checks (Windows):
```powershell
pwsh scripts/env/check_virtualization.ps1 -Json virt_report.json
```
Inspect `virt_report.json` for readiness flags.

---
## 16. Roadmap (Indicative)
- Additional indicators (momentum, volatility clustering)
- Portfolio-level multi-symbol extension
- Advanced execution (queue modeling, partial fills)
- Coverage badge publication (Codecov)
- WebSocket multiplex (evaluation vs SSE)
- Enhanced validation visualization support

---
## 17. License
MIT License – see `LICENSE` (if not present, add before external distribution).

---
## 18. Acknowledgements
Developed with a focus on small, test-first increments and explicit contracts. Inspired by practical needs of systematic strategy research and reproducibility discipline.

---
**Quick Start Recap**
```powershell
poetry install --with dev
poetry run uvicorn api.app:app --reload
# Submit a run
curl -X POST http://localhost:8000/runs -H "Content-Type: application/json" -d '{"symbol":"TEST","timeframe":"1m","start":"2024-01-01","end":"2024-01-02","indicators":[{"name":"sma","params":{"window":5}},{"name":"sma","params":{"window":15}}],"strategy":{"name":"dual_sma","params":{"fast":5,"slow":15}},"risk":{"model":"fixed_fraction","params":{"fraction":0.1}},"execution":{"slippage_bps":0,"fee_bps":0},"validation":{},"seed":42}'
```

> Keep this README as a living contract: update Data Flow & Extensibility sections first when architecture evolves.
