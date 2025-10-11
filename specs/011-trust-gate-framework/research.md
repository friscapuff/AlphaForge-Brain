# Research: Trust Gate Framework (Phase 0)

Feature: 011-trust-gate-framework
Date: 2025-10-11
Spec: specs/011-trust-gate-framework/spec.md
Plan: specs/011-trust-gate-framework/plan.md

## 1. Integrity & Validation Inventory
| Area | Current Implementation | Key Files | Notes | Gaps for Feature |
|------|-----------------------|-----------|-------|------------------|
| Deterministic replay & hashing | `poetry run run-hash` verifies run manifests and artifact hashes | `alphaforge-brain/src/services/cli/run_hash.py`, `alphaforge-brain/src/services/hash_service.py` | Produces golden baseline hashes but no automated comparison to prior canonical run. | Need canonical baselines stored + signed; trust gate harness must diff against baseline and manage regeneration lifecycle. |
| Masters validation suite | Permutation, CPCV leakage, execution realism | `alphaforge-brain/src/domain/validation/` | Ensures statistical defensibility, generates `validation_detail.json`. | Must run only after trust gates succeed; requires gating orchestrator and manifest cross-linking. |
| Ingest idempotency tooling | Ad-hoc regression scripts, manual hash checks | `scripts/ingest/hash_ingest_snapshot.py` (exploratory), `alphaforge-brain/src/services/ingest/` | No automated reruns per build, no vendor metadata capture. | Gate must repeat ingest with deterministic cache busting and compare dataset hashes + schema versions, storing vendor version info. |
| Timezone normalization | Exchange calendars enforce trading sessions | `alphaforge-brain/src/lib/timezones.py`, `alphaforge-brain/src/domain/calendars/` | Handles UTC conversions during ingest; DST transitions validated manually. | Gate needs synthetic timezone fixture dataset and DST/holiday assertions with failure diagnostics. |
| Universe control | Universe manifests tracked in onboarding scripts | `scripts/universe/stamp_universe.py`, data under `presets/universe/` | Delisted symbol preservation audited manually. | Gate must compute hash stamps across ingest outputs and alert on missing symbols or vendor drift. |
| Accounting reconciliation | Equity vs trade ledger reconciliation script in analytics notebooks | `alphaforge-brain/src/services/accounting/reconcile.py` (requires consolidation) | Not wired into CI; tolerances informal. | Gate must formalize round-trip reconciliation with tolerances recorded in config + manifest. |

## 2. Gate-Specific Research Highlights
- **Golden-Run Determinism**
  - Baseline artifacts live in `zz_artifacts/perf_baseline.json` and `run_hash_phase7_snapshot.json`; need canonical `golden_run/` directory with manifest, hash digests, and dataset lineage.
  - Baseline regeneration currently manual via `scripts/replays/golden_run.py`; requires governance hook for version rev.

- **Causality (Leak-Catcher)**
  - Synthetic datasets reside under `presets/leak_catcher/`; seeds defined in `presets/leak_catcher/config.yaml` (versioned by git hash).
  - Must document fallback when dataset shorter than strategy warm-up; plan to maintain deterministic alternate dataset `leak_catcher_short.parquet`.
  - Need measurement thresholds: Sharpe |equity drift| ≤ 1e-6, leakage score ≤0.05.

- **Ingest Idempotency**
  - Ingest orchestrator `alphaforge-brain/src/services/ingest/pipeline.py` accepts `run_mode` flags; add `dry-run` to avoid double persistence but still compute hashes.
  - Vendor metadata from `exchange-calendars` & API responses stored in temp logs; gate must persist `vendor_version`, `api_rate_limit_hits` for audit.

- **Timezone Normalization**
  - Use `exchange-calendars` trading calendars plus `pytz` conversions; DST boundary tests exist in `tests/unit/lib/test_timezones.py` but limited coverage.
  - Gate should replay sample bars across NYSE, LSE, TSE to ensure UTC and sequential ordering.

- **Universe Stamp**
  - Historical ticker lists stored in `data/universe_snapshots/*.csv`; hashed manually with `scripts/universe/hash_snapshot.py`.
  - Gate must compare ingest output universe to canonical stamp and log missing symbols with vendor dataset correlation ID.

- **Equity & Accounting Reconciliation**
  - Accounting ledger saved in SQLite `accounting_ledger` table with trades, fills, costs; equity curves generated via `services/performance/equity_curve.py`.
  - Need deterministic tolerance: ±0.01 currency units or 5 bps relative difference whichever higher.

## 3. Observability & Performance Considerations
- Emit structlog events per gate: `event="trust_gate", gate="golden_run"`, include `status`, `duration_ms`, `tolerance`, `correlation_id`.
- Prometheus metrics: `trust_gate_duration_seconds`, `trust_gate_status{gate}` gauge (0/1), `trust_gate_failures_total{gate}` counter.
- Benchmark integration: Extend `scripts/bench/perf_run.py` to record `trust_suite.total` span; target < 1.5× Masters runtime.
- Logging volume caution: Provide log sampling for steady-state success but retain full diagnostics on failure.

## 4. Persistence & Contract Impact
| Artifact | Change Needed | Backward Compatibility Strategy |
|----------|---------------|----------------------------------|
| Trust Gate Report (`trust_gate_report.json`) | New signed JSON artifact listing each gate result, tolerances, baseline hashes, vendor metadata. | Versioned schema (`v1`); Mind treats absence as "trust gates disabled" for historical runs. |
| Run Manifest (`manifests/{run_id}.json`) | Add `trust_gate` section with summary + correlation IDs for artifacts. | Default to `status:"not_executed"` for older runs; ensure manifest schema version bump with fallback semantics. |
| SQLite (`trust_gate_results`, `trust_gate_baselines`) | New tables storing per-run results and canonical baselines. | Add via Alembic migration with nullable columns, no impact on existing tables. |
| API `GET /runs/{id}` | Include trust gate status summary and artifact links. | Add optional field; Mind uses feature flag to display when present. |
| Mind UI badges | Add status badges pulling from API/manifest. | Default to "Not Available" state when backend lacks data. |

## 5. Risk Register
| Risk | Category | Impact | Likelihood | Mitigation | Trigger |
|------|----------|--------|------------|------------|---------|
| Baseline skew after intentional algorithm change | Data Integrity | High | Medium | Governance workflow for baseline regeneration + signed approvals. | Hash mismatch flagged between baseline and expected version. |
| Leak-catcher dataset insufficient length | Correctness | Medium | Medium | Maintain alternate dataset; detect warm-up insufficiency and auto-switch with log. | Gate detects `len < warmup + margin`. |
| Vendor rate limiting blocks idempotent ingest | Operational | Medium | Medium | Implement exponential backoff with deterministic schedule and record attempts; allow waiver on repeated 429s. | Repeated 429/503 responses beyond threshold. |
| Timezone gate false positives due to leap seconds | Correctness | Low | Low | Incorporate leap-second table, treat as warning not failure, escalate for manual review. | Encounter timestamp flagged as leap second. |
| Accounting reconciliation drift due to floating precision | Correctness | Medium | Medium | Use decimal for ledger compare, tolerance of max(0.01, 5bps). | Drift > tolerance. |
| Performance regression from full suite | Performance | Medium | Medium | Parallelize independent gates, reuse cached datasets, monitor runtime via benchmark. | `trust_suite.total` > 1.5× Masters SLA. |

## 6. Decision Log
| # | Decision | Rationale | Revisit Trigger |
|---|----------|-----------|-----------------|
| 1 | Store baselines under `artifacts/trust_gates/baselines/` with signed manifest | Centralized access + audit trail | Storage growth > 2× per quarter |
| 2 | Use JSON artifact with detached signature instead of embedded signature | Allows downstream parsing w/out crypto libs | Signing workflow changes or compliance request |
| 3 | Leverage structlog for per-gate events, Prometheus for metrics | Align with constitution observability mandates | Observability stack migration |
| 4 | Enforce CLI entrypoint `poetry run trust-gates` with `--only` option | Satisfy FR-201, FR-213 and enable local focus runs | CLI explosion; consider config file approach |
| 5 | Parallelize ingest + timezone gates when resources allow | Reduce total runtime while keeping determinism | Resource contention or nondeterministic ordering |
| 6 | Persist vendor metadata (`vendor_version`, `retrieved_at`, `api_endpoint`) with run | Provide forensic capability for ingest drift | Compliance guidelines limit metadata retention |
| 7 | Default tolerance for accounting reconciliation = max(0.01, 5 bps) | Balances float noise vs meaningful drift | Detection of frequent borderline failures |
| 8 | Fail suite on missing baseline unless waiver present | Prevent silent degradation | Baseline intentionally deprecated without replacement |

## 7. Open Questions
1. Do we need encrypted storage for baseline artifacts given they include vendor dataset hashes? (Pending security review.)
2. Should trust gate metrics appear in existing validation dashboards or a dedicated dashboard? (Coordinate with Mind team.)

## 8. Phase 0 Exit Criteria
- Integrity inventory documented ✔️
- Gate-by-gate research captured ✔️
- Observability & performance expectations enumerated ✔️
- Persistence & contract impacts outlined ✔️
- Risks and decisions logged ✔️
- Open questions recorded for follow-up ✔️
