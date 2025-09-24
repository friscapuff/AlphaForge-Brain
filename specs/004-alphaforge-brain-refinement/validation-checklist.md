# Validation Checklist (Plain Language)

This checklist connects each Feature Requirement (FR) to the exact tests or artifacts that prove it works. It’s designed for non‑technical readers who want to verify outcomes without reading code.

How to read this: For each FR, you’ll see the goal in plain words, what we check, and where the evidence lives (tests or artifacts).

## Persistence (FR-100–105, FR-140–142)
- FR‑100 Database schema present and loadable
  - Evidence: SQLite schema dump artifact in CI; creation/migration scripts succeed
- FR‑101 Persist manifest and configuration
  - Evidence: `runs` table contains manifest JSON and hashes; validated by round‑trip integration test
- FR‑102 Record trades and equity at finalize
  - Evidence: Integration test reconstructs equity/trades from DB and matches expected content
- FR‑103 Persist provenance (db version, seeds)
  - Evidence: `runs` row includes `db_version` and seeds; unit/integration tests read back these values
- FR‑104 Typed read helpers available
  - Evidence: Tests call typed accessor to fetch run information
- FR‑105 Persist validation rows and metrics
  - Evidence: Validation inserts are visible in `validations` and `phase_metrics` tables
- FR‑140 Canonical JSON + content hashes
  - Evidence: Hash metrics saved at init; deterministic replay tests verify stability
- FR‑141 Manifest validated against schema
  - Evidence: Schema validation test passes with correct input
- FR‑142 Replay and round‑trip integrity
  - Evidence: Persistence round‑trip test re‑materializes artifacts and matches hashes

## Causality & Determinism (FR-110–113, FR‑151)
- FR‑110 Causality guard modes (STRICT/PERMISSIVE)
  - Evidence: Unit tests verify behavior; policy recorded in metrics
- FR‑111 Guard stats surfaced in metrics
  - Evidence: `phase_metrics` rows contain guard statistics
- FR‑112 No look‑ahead in features/indicators
  - Evidence: Feature enforcement tests confirm no peeking into the future
- FR‑113 Guard mode and stats stored
  - Evidence: Persistence test shows guard mode and counts stored
- FR‑151 Determinism replay harness
  - Evidence: Deterministic two‑run replay tests pass and hashes match

## Statistical Breadth (FR-120–124, FR‑152)
- FR‑120 HADJ‑BB heuristic works with fallback
  - Evidence: Unit tests show heuristic picks a block size; weak/short data uses IID fallback
- FR‑121 Bootstrap engine and deterministic distributions
  - Evidence: Validation tests confirm reproducible distributions for fixed seeds
- FR‑122 CI width policy enforced
  - Evidence: CI gate script and tests fail on too‑wide intervals in STRICT mode
- FR‑123 Walk‑forward aggregator summarizes windows
  - Evidence: Validation runner aggregates and exposes summary fields
- FR‑124 Validation artifacts integrated
  - Evidence: Merge summaries produced and persisted
- FR‑152 Bootstrap CI width gate in CI
  - Evidence: Acceptance suite runs width gate; artifact uploaded

## Pipeline & Memory (FR-130–132)
- FR‑130 Deterministic chunk iterator
  - Evidence: Unit tests confirm chunk boundaries and determinism
- FR‑131 Chunked feature builder matches monolithic
  - Evidence: Integration test shows identical feature results and cache determinism
- FR‑132 Memory reduction benchmark
  - Evidence: Bench harness measures and asserts expected reduction threshold

## Observability & CI (FR-150–158)
- FR‑150 Migration verification and head checksum
  - Evidence: CI step verifies migration head file; parity script present
- FR‑151 Determinism replay in CI
  - Evidence: CI job executes replay and uploads artifact
- FR‑152 Bootstrap CI width gate wired into CI
  - Evidence: CI job invokes gate; acceptance suite summarizes
- FR‑153 Schema dump artifact
  - Evidence: CI uploads `schema.sql` for review
- FR‑154 Phase timing metrics
  - Evidence: `phase_metrics` timing rows present per phase
- FR‑155 Lightweight tracing spans
  - Evidence: Span markers recorded and queryable
- FR‑156 Error logging persistence
  - Evidence: `run_errors` table populated on failures
- FR‑157 Phase completion markers
  - Evidence: Marker rows recorded and reflected in manifest metadata
- FR‑158 Minimal credential provider
  - Evidence: Env‑based credential stub available

## Documentation (FR-160–162)
- FR‑160 Contracts appendix present
  - Evidence: `contracts-appendix.md` exists and is linked in README
- FR‑161 Persistence quickstart present
  - Evidence: `persistence-quickstart.md` exists and is linked in README
- FR‑162 README describes persistence, validation, chunk mode
  - Evidence: README updated with clear links and explanations

## Sign‑Off Readiness
- All related tests pass (unit, integration, validation, e2e)
- CI acceptance suite passes (determinism replay + width gate)
- Documentation complete for users to understand outcomes
