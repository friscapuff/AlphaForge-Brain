# Feature Specification: AlphaForge Brain Stability & Truthfulness Refinement

**Feature Branch**: `005-refine-alphaforge-brain`
**Created**: 2025-09-25
**Status**: Draft (Planning)
**Input**: User description: "Refine AlphaForge Brain by prioritizing infrastructure stability and truthfulness of results over feature expansion, ensuring the system can scale reliably when multiple runs and sweeps are introduced without compromising financial realism. The data pipeline should be hardened with chunked and Arrow-based I/O, moving away from raw Pandas workflows to prevent memory blowups, while SQLite is expanded into a canonical schema with dedicated tables for runs, trades, equity curves, features, and validation outputs, each carrying hashes, seeds, and indices to guarantee reproducibility, provenance, and fast retrieval. Reliability of results must be reinforced by explicitly enforcing corporate action adjustments at ingest, persisting dataset digests and adjustment policies, and locking causality with a central .shift(1) guard to ensure no same-bar information leaks into fills. Execution realism should be maintained by consistently applying fees and slippage on both entry and exit and documenting the latency model (next-bar open), while validation must rely on seeded block bootstraps with jitter, permutation, and walk-forward splits, all wired to CI so builds fail on nondeterminism, contract drift, or resource overuse. Integration points for AlphaForge Mind should be stabilized early by freezing a minimal API contract, publishing a thin client SDK, and shipping a “hello-run” workflow that submits a config, streams seeded events, and retrieves artifacts deterministically. Infrastructure stress testing should be added at the CI level: running the same reference strategy twice in parallel, sweeping a bounded grid, and asserting determinism, cache reuse, artifact byte-stability, and memory ceilings to simulate multi-strategy load without building new strategies prematurely. Documentation must clarify these contracts—required columns, adjustment policies, execution timing, seed derivation, slippage/fee semantics, and SQLite’s role—while also offering a quickstart guide for Mind integration. By focusing only on determinism, data integrity, contract enforcement, and reproducibility, AlphaForge Brain can deliver reliable, realistic, and cost-efficient research outcomes while avoiding scope creep into multi-asset or indicator bloat."

## Execution Flow (main)
```
1. Parse user description from Input
   → Identify: stability, determinism, scalability, realism, CI gates, Brain↔Mind integration
2. Extract key concepts & constraints
   → Arrow-based I/O, chunked pipeline, SQLite canonical schema, corporate actions, causality guard, seeded validations, API freeze
3. Mark ambiguities
   → Use [NEEDS CLARIFICATION] for unresolved policies (retention, CI limits)
4. Define User Scenarios & Testing
   → Deterministic replays, parallel runs, bounded sweep, client SDK “hello-run”
5. Generate Functional Requirements
   → Testable, observable outcomes; CI enforcements
6. Identify Key Entities
   → Runs, Trades, Equity, Features, Validation, Datasets, Policies
7. Review Checklist
   → Ensure scope is bounded to stability & truthfulness; no feature creep
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT and WHY (stability, determinism, realism, scale)
- ❌ Avoid unnecessary HOW (implementation details), except at contract boundaries
- 👥 Written for stakeholders; emphasize guarantees and CI enforcement
- 🔗 Separate Brain (compute, persistence, contracts) from Mind (client/SDK, UX)

### Section Requirements
- Mandatory: User Scenarios & Testing, Functional Requirements, Key Entities, Review Checklist
- Optional: Cross-Project Boundary (included here due to Brain↔Mind integration)

---

## Clarifications

### Session 2025-09-25
- Q: Which corporate action adjustment policy should Brain enforce at ingest for the canonical dataset and run hashing? → A: Fully adjusted prices (splits + dividends) at ingest; store adjusted series only; persist policy and factors digest
- Q: Which CI profile should we adopt for seeded bootstrap/permutation/walk-forward gates? → A: Bootstrap: 500 trials @ 95% CI; Permutation: 500; Walk-forward: 5 splits; STRICT fail on nondeterminism
- Q: What memory ceiling policy should be enforced for CI and local runs? → A: CI: 1.5 GB max RSS; Local: warning at 2.0 GB, soft fail at 3.0 GB (balanced)
- Q: What data retention and artifact versioning policy should Brain enforce? → A: Tiered retention. Keep full artifacts for the last 50 runs (globally). Additionally, maintain the top 5 runs per strategy test at full fidelity. Provide manual pin/save to mark “winning” runs that are never evicted unless explicitly unpinned. Beyond these, retain only minimal manifests/metrics and SQLite rows; evict large blobs with a rehydrate hook.
- Q: What execution timing and timestamping model should Brain enforce? → A: Next-bar open fills; features computed on bar close with .shift(1); on gaps/halts, skip fills until the next available session open; slippage and fees applied on both entry and exit.
- Q: What is the bounded parameter grid size (N) for CI sweeps? → A: N = 20 variants (CI default) to bound time/memory deterministically.
- Q: What are the pipeline chunking defaults? → A: Default target chunk memory ≈ 256 MB with adaptive sizing; overlap equals max lookback L; CI hard row cap = 2,000,000 rows per chunk; memory sampler backpressures when RSS > 1.2 GB.

---

## User Scenarios & Testing (mandatory)

### Primary User Story
As a research engineer, I need AlphaForge Brain to produce reproducible, realistic results and scale to parallel runs and small sweeps without memory blowups, so I can trust outcomes and iterate quickly.

### Acceptance Scenarios
1. Given a fixed dataset digest and config, When I run the same job twice (sequentially or in parallel), Then I get identical run and artifact hashes and matching DB row digests (deterministic replay).
2. Given a bounded parameter grid (≤ 20 variants in CI), When I submit a sweep, Then cache reuse prevents duplicate feature recomputation and total memory stays under the configured ceiling (CI cap 1.5 GB); CI fails otherwise.
3. Given a dataset with corporate actions, When I ingest, Then fully adjusted prices (splits + dividends) are applied deterministically, policy and factors digest are recorded, and the dataset digest incorporates the adjustments; re-ingest matches prior digest.
4. Given the API contract frozen to a minimal surface, When Mind submits a “hello-run” via SDK, Then it can stream seeded events and fetch deterministic artifacts with no contract drift.
5. Given seeded validations with CI defaults, When CI runs, Then Bootstrap 500 @95% CI, Permutation 500, Walk-forward 5 splits execute deterministically; any nondeterminism causes STRICT failure.
6. Given causality guard is enabled, When a strategy attempts same-bar data access, Then STRICT mode fails the run; PERMISSIVE records violations and surfaces them in metrics/manifest.
7. Given 60 completed runs exist across strategies, When the retention job executes, Then the most recent 50 runs remain at full-fidelity unless superseded by pinning/eviction rules; for each strategy test, the top 5 runs by the configured primary metric remain full-fidelity; unpinned, non-top-k older runs are demoted to manifest-only (SQLite + metrics retained, blobs evicted) with an audit entry. Pinned “winning” runs are never evicted.
8. Given a signal generated at bar close and a trading halt occurs at the next session open, When execution is attempted, Then no fill occurs during the halt; the order is executed at the first subsequent available session open with configured slippage and fees; all timestamps reflect next-bar open fills and features at prior bar close (shifted by one).

### Edge Cases
- Very long series (high-frequency): chunk iterator preserves order and overlap; outputs match monolithic reference (hash-equivalent).
- Corporate action data missing/partial: ingest fails with explicit error and guidance; no silent defaults.
- SQLite schema migration drift: CI halts on missing migration or head checksum mismatch.
- Concurrent identical runs: returned run_hash is reused and DB writes are idempotent.
- Retention conflicts: If a run is both in top-5 and pinned, it remains pinned; if top-5 status changes after new runs, previously protected runs may be demoted unless pinned.
- Gap/halts: If the next-bar open is missing due to market closure, fills are deferred to the next available session open; there is no same-bar or intra-bar execution.

## Requirements (mandatory)

### Functional Requirements
- FR-101 (Determinism): Identical config + dataset digest yields identical run_hash, artifact hashes, and DB row digests, even under parallel execution.
- FR-102 (Pipeline memory): Feature pipeline supports chunked processing with Arrow-based I/O; outputs are hash-equivalent to monolithic; memory stays below a configurable ceiling. CI memory ceiling: 1.5 GB max RSS; Local: warning at 2.0 GB, soft fail at 3.0 GB. Defaults: target ~256 MB per chunk (adaptive); overlap = max lookback L; CI hard cap 2,000,000 rows/chunk; memory sampler backpressures >1.2 GB RSS.
- FR-103 (SQLite canonical schema): Define dedicated tables (runs, trades, equity, features, validation) with indices and persisted content hashes, seeds, and timestamps.
- FR-104 (Corporate actions): Enforce fully adjusted prices (splits + dividends) at ingest; persist adjustment policy and factors digest; dataset digest MUST incorporate adjustments; adjusted series are canonical.
- FR-105 (Causality): Enforce central .shift(1) guard for features/signals; STRICT fails on same-bar access; PERMISSIVE records violations and counts.
- FR-106 (Execution realism): Enforce execution timing and costs.
  - Latency model: fills at next-bar open.
  - Feature timestamping: features/signals computed on bar close and shifted by one (.shift(1)).
  - Gap/halts policy: if the next session open is unavailable (halt/holiday), defer fills to the first subsequent available session open; no intra-bar execution.
  - Costs: slippage and fees applied on both entry and exit consistently and persisted in manifests and trade rows.
- FR-107 (Seeded validations): Provide seeded block bootstrap with jitter, permutation test, and walk-forward splits; persist method metadata and CI-width gates. CI defaults: Bootstrap 500 trials @95% CI; Permutation 500 trials; Walk-forward 5 splits.
- FR-108 (API freeze & SDK): Freeze minimal API contract for Mind; publish thin client SDK; provide a “hello-run” workflow (submit, stream, retrieve deterministically).
- FR-109 (CI gates): CI fails on nondeterminism, OpenAPI/contract drift, migration head mismatch, or exceeding configured resource ceilings (time/memory); STRICT failure mode enforced for determinism checks under CI defaults and CI memory cap 1.5 GB RSS.
- FR-110 (Stress tests): CI stress job runs two identical runs in parallel + a bounded sweep; asserts determinism, cache reuse, artifact byte-stability, and memory ceilings.
- FR-111 (Documentation): Document required columns, adjustment policies, execution timing, seed derivation, slippage/fee semantics, and SQLite roles; include Mind quickstart.
- FR-113 (Performance benchmarks): Provide benchmark tests and CI thresholds to enforce (a) observability overhead < 3% relative to baseline, (b) bootstrap runtime ≤ 1.2× IID baseline for CI defaults, and (c) memory sampler overhead within acceptable bounds (< 1% runtime impact). Persist benchmark metrics with schema/api versions.
- FR-112 (Retention & Eviction): Implement tiered retention and safe eviction.
  - Defaults: keep full artifacts for the most recent 50 runs (global). Additionally, keep top 5 runs per strategy test (full fidelity) ranked by that test’s primary metric. Manual pin/save allows marking “winning” runs to prevent eviction.
  - Eviction behavior: demote unpinned, non-top-k older runs to manifest-only: retain SQLite rows, run manifest, metrics, and content hashes; evict large blobs (features, equity, parquet, other bulky artifacts). Provide a rehydrate hook to rebuild evicted artifacts deterministically.
  - Safety & observability: maintain an immutable audit log for pin/unpin and eviction events with actor, timestamp, reason. CI must not perform destructive eviction; CI simulates policy and asserts correct tagging.
  - APIs: expose list/pin/unpin/rehydrate endpoints and CLI commands; surface retention_state on run objects (e.g., full, manifest-only, evicted, pinned, top_k).

### Cross-Project Boundary (Brain vs Mind)
- Brain responsibilities: deterministic compute, persistence (SQLite), validation engines, causality/execution policies, OpenAPI, artifact/manifest contracts, CI gates.
- Mind responsibilities: SDK thin client (submit config, stream events, fetch artifacts), no simulation logic, adheres to frozen API.

### Key Entities (data)
- Run: config_hash, run_hash, seed_root, created_at, status, manifest_json, dataset_digest, retention_state, pinned (bool), pinned_by, pinned_at, primary_metric_name, primary_metric_value, rank_within_strategy, latency_model (e.g., "next_bar_open"), feature_timestamping (e.g., "bar_close_shift1"), gap_policy (e.g., "defer_to_next_session_open").
- Trades: ts, side, qty, fill_price, fees, slippage, pnl, position_after, indices; content_hash.
- Equity: ts, equity, drawdown, realized/unrealized pnl; content_hash.
- Features: spec_hash, rows, cols, digest, build_policy (chunk/overlap), cache linkage.
- Validation: permutation p-value; bootstrap metadata (method, block_length, jitter, fallback), CI width; walk-forward aggregates.
- Dataset & Policies: raw_digest, adjustment_policy = "full-adjusted" (splits + dividends), adjustment_factors_digest, adjusted_digest, calendar_id, tz.
- AuditLog: event_type (pin, unpin, evict, rehydrate), run_hash, actor, ts, details_json.

---

## Review & Acceptance Checklist

### Content Quality
- [ ] No unnecessary implementation details (framework specifics avoided)
- [ ] Focused on user value: stability, determinism, realism, scale
- [ ] Written for stakeholders; clear guarantees and measurable outcomes

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria measurable (hash-equality, CI gates, memory/time bounds)
- [ ] Scope bounded (no multi-asset/indicator expansion)
- [ ] Brain/Mind boundary defined

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed
