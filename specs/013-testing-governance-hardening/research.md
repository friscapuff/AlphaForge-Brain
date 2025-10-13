# Research Notes: Testing Governance Hardening

## Trust Gate Tolerance SLAs
- **Decision**: Fail closed when tolerance config is missing/malformed; load versioned YAML under `configs/trust_gates/tolerances/` and emit `trust_gate_config_error` metric alongside gate failure.
- **Rationale**: Aligns with Constitution Principle I (determinism) and VII (causality safety) by preventing unpredictable runs; ensures auditability with explicit metric and manifest entry.
- **Alternatives Considered**:
  - Fail open with warning (rejected: allows uncontrolled promotions).
  - Auto-fallback to last known SLA (rejected: risks silent drift and violates traceability).

## Validation Go/No-Go Enforcement
- **Decision**: Orchestrator marks runs as `FAILED_VALIDATION` when Masters validation thresholds breach; API prevents promotion and retention treats status as non-promotable without waiver.
- **Rationale**: Converts passive metrics into gating aligned with FR-003/004, reduces manual oversight.
- **Alternatives Considered**:
  - Retain caution flags only (rejected: governance gap remains).
  - Require manual override per run (rejected: undermines automation goals).

## Persistence Schema Versioning
- **Decision**: Embed `schema_version` on every persisted payload, validate via JSON Schema in `contracts/persistence/`, and publish migration scripts under `scripts/migrations/` for any version bump.
- **Rationale**: Satisfies FR-005/006 and Constitution Principle X by providing deterministic upgrade paths.
- **Alternatives Considered**:
  - Implicit schema inference (rejected: opaque drift, difficult audits).
  - Schema version stored only in database metadata (rejected: API consumers lose visibility).

## Accounting Invariants Module
- **Decision**: Implement dedicated module under `services/trust_gates/accounting` asserting `cash + unrealized_pnl + fees = equity` within configurable tolerances; log offending trade IDs and surface via Prometheus metrics.
- **Rationale**: Addresses FR-007/008 with auditable evidence; integrates naturally with existing trust gate suite.
- **Alternatives Considered**:
  - Embed checks inside existing equity service (rejected: couples unrelated responsibilities).
  - Rely on regression scripts only (rejected: lacks runtime enforcement).

## Retention & Pinning Policy Automation
- **Decision**: Enforce defaults from `configs/retention/policy.yaml`, skip eviction when pins exceed budgets, log breach, and require waiver or policy update before eviction; extend CLI (`poetry run retention ...`) to manage pins with audit trail.
- **Rationale**: Upholds FR-009/010 and Constitution Principle V by maintaining deterministic storage while respecting deliberate pins.
- **Alternatives Considered**:
  - Force eviction despite pins (rejected: loses curated evidence).
  - Pause retention entirely (rejected: storage drift).

## Runtime Cross-Root Guard
- **Decision**: Install import hook in `alphaforge-brain` startup that blocks Mind imports, integrate with Ruff custom rule, and document in Constitution/Developer guides.
- **Rationale**: Enforces FR-011/012 and Constitution Principle IX; provides defense-in-depth beyond CI.
- **Alternatives Considered**:
  - Rely solely on existing CI script (rejected: runtime environments remain vulnerable).
  - Use only documentation/education (rejected: insufficient enforcement).

## Coverage Implications
- Each governance decision mandates fail-closed regression tests plus negative-path coverage to demonstrate enforcement (reflected in tasks T005–T029).
- Prometheus counters and audit logs are treated as first-class evidence; capture snapshots during every regression run to prove FR-001…FR-012 compliance.
- Import guard enforcement combines unit tests, integration tests, and lint fixtures to ensure multi-layer protection without introducing false positives.
