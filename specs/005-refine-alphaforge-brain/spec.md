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

## User Scenarios & Testing (mandatory)

### Primary User Story
As a research engineer, I need AlphaForge Brain to produce reproducible, realistic results and scale to parallel runs and small sweeps without memory blowups, so I can trust outcomes and iterate quickly.

### Acceptance Scenarios
1. Given a fixed dataset digest and config, When I run the same job twice (sequentially or in parallel), Then I get identical run and artifact hashes and matching DB row digests (deterministic replay).
2. Given a bounded parameter grid (≤ N variants), When I submit a sweep, Then cache reuse prevents duplicate feature recomputation and total memory stays under a configured ceiling; CI fails otherwise.
3. Given a dataset with corporate actions, When I ingest, Then adjustments are applied deterministically, policies recorded, and the dataset digest incorporates adjustments; re-ingest matches prior digest.
4. Given the API contract frozen to a minimal surface, When Mind submits a “hello-run” via SDK, Then it can stream seeded events and fetch deterministic artifacts with no contract drift.
5. Given bootstrap/permutation/walk-forward validations are seeded, When CI runs, Then builds fail on nondeterminism, contract drift, or resource overuse (time/memory gates).
6. Given causality guard is enabled, When a strategy attempts same-bar data access, Then STRICT mode fails the run; PERMISSIVE records violations and surfaces them in metrics/manifest.

### Edge Cases
- Very long series (high-frequency): chunk iterator preserves order and overlap; outputs match monolithic reference (hash-equivalent).
- Corporate action data missing/partial: ingest fails with explicit error and guidance; no silent defaults.
- SQLite schema migration drift: CI halts on missing migration or head checksum mismatch.
- Concurrent identical runs: returned run_hash is reused and DB writes are idempotent.

## Requirements (mandatory)

### Functional Requirements
- FR-101 (Determinism): Identical config + dataset digest yields identical run_hash, artifact hashes, and DB row digests, even under parallel execution.
- FR-102 (Pipeline memory): Feature pipeline supports chunked processing with Arrow-based I/O; outputs are hash-equivalent to monolithic; memory stays below a configurable ceiling.
- FR-103 (SQLite canonical schema): Define dedicated tables (runs, trades, equity, features, validation) with indices and persisted content hashes, seeds, and timestamps.
- FR-104 (Corporate actions): Enforce corporate action adjustments at ingest; persist adjustment policy and integrate into dataset digest/provenance.
- FR-105 (Causality): Enforce central .shift(1) guard for features/signals; STRICT fails on same-bar access; PERMISSIVE records violations and counts.
- FR-106 (Execution realism): Apply slippage/fees on entry and exit consistently; document latency model (next-bar open) and persist in manifest.
- FR-107 (Seeded validations): Provide seeded block bootstrap with jitter, permutation test, and walk-forward splits; persist method metadata and CI-width gates.
- FR-108 (API freeze & SDK): Freeze minimal API contract for Mind; publish thin client SDK; provide a “hello-run” workflow (submit, stream, retrieve deterministically).
- FR-109 (CI gates): CI fails on nondeterminism, OpenAPI/contract drift, migration head mismatch, or exceeding configured resource ceilings (time/memory).
- FR-110 (Stress tests): CI stress job runs two identical runs in parallel + a bounded sweep; asserts determinism, cache reuse, artifact byte-stability, and memory ceilings.
- FR-111 (Documentation): Document required columns, adjustment policies, execution timing, seed derivation, slippage/fee semantics, and SQLite roles; include Mind quickstart.

### Cross-Project Boundary (Brain vs Mind)
- Brain responsibilities: deterministic compute, persistence (SQLite), validation engines, causality/execution policies, OpenAPI, artifact/manifest contracts, CI gates.
- Mind responsibilities: SDK thin client (submit config, stream events, fetch artifacts), no simulation logic, adheres to frozen API.

### Key Entities (data)
- Run: config_hash, run_hash, seed_root, created_at, status, manifest_json, dataset_digest.
- Trades: ts, side, qty, fill_price, fees, slippage, pnl, position_after, indices; content_hash.
- Equity: ts, equity, drawdown, realized/unrealized pnl; content_hash.
- Features: spec_hash, rows, cols, digest, build_policy (chunk/overlap), cache linkage.
- Validation: permutation p-value; bootstrap metadata (method, block_length, jitter, fallback), CI width; walk-forward aggregates.
- Dataset & Policies: raw_digest, adjustment_policy, adjusted_digest, calendar_id, tz.

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
