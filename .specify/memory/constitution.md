<!--
Sync Impact Report
Version: 1.3.0 → 1.4.0 (MINOR)
Modified Principles: II. Test-First & Traceability (embedded 90% coverage + fail-closed gates), V. Observability & Forensic Auditability (codified trust-gate metrics + signed artifacts), VI. Performance Discipline (profiling harness + regression alerts), VII. Data Integrity & Causality Safety (schema_version, tolerance SLAs, retention enforcement), IX. Multi-Project Architecture (runtime import guard), X. Contract Versioning & Backward Compatibility (schema IDs), NEW XI. Automated Governance & Waiver Discipline.
Added Sections: XI. Automated Governance & Waiver Discipline.
Removed Sections: None.
Templates Requiring Updates:
	.specify/templates/plan-template.md (⚠ reference tolerance SLA + retention checkpoints in acceptance tasks)
	.specify/templates/spec-template.md (⚠ require coverage ≥90% + signed config change notes)
	.specify/templates/tasks-template.md (⚠ include waiver cadence + trust gate artifact deliverables)
	.specify/templates/agent-file-template.md (⚠ mention runtime import guard checks during analysis)
Follow-up TODOs:
	- Wire schematized tolerance/retention validation CI step into plan/spec templates.
	- Document runtime import guard troubleshooting flow in docs/operations/trust_gates.md by 2025-10-31.
-->

# AlphaForge Constitution

## Core Principles

### I. Determinism First (NON-NEGOTIABLE)
All computations MUST be reproducible from a single configuration + seed root. Any nondeterministic source (wall clock time, unsorted parallel reductions, random generators) MUST be explicitly seeded or eliminated. CI replays enforce hash + semantic equivalence; divergence blocks merge.

### II. Test-First & Traceability (NON-NEGOTIABLE)
Every Functional Requirement (FR) MUST map to at least one failing test before implementation. Commits MUST reference FR IDs (e.g., FR-120) in their message. Code without demonstrable test coverage is rejected. Quality gates and coverage enforcement MUST fail closed with global coverage floors ≥90% across line, branch, integration, and function metrics; negative-path fixtures remain mandatory to prove gates detect seeded regressions. Removal of a test requires documented FR deprecation and governance approval.

### III. Modular MVC & Bounded Contexts
Architecture enforces an explicit dual-project separation:
	- Project A: alphaforge-brain (backend simulation & analytics core, domain + persistence + services layers)
	- Project B: alphaforge-mind (frontend UI/visualization & interactive orchestration)
Each project follows MVC (or MV* variant) boundaries:
	- Models: Pure domain/data logic (no IO side-effects)
	- Views (Mind): Presentation & user interaction only
	- Controllers/Services: Orchestrate workflows, enforce invariants
Cross-project interaction occurs ONLY through versioned contracts (API/IPC or serialized artifact schemas). Direct module imports across project roots are forbidden.
Runtime import guards and lint rules enforce these boundaries in development, CI, and production; violations raise descriptive exceptions and block promotion until resolved or waived.

### IV. Simplicity & Minimal Surface
Prefer minimal abstractions; introduce layers only when they reduce coupling or encode stable contracts. Feature creep MUST be justified with user value or risk mitigation. Dead code is removed proactively. Complexity > benefit triggers refactor tasks.

### V. Observability & Forensic Auditability
All phases emit structured timing + tracing spans. Errors persist with minimal, hash-stable diagnostic context. Provenance (hashes, schema version, seeds, config) MUST allow reconstruction of any historical run and its derived views in Mind. Trust-gate and Masters validation suites MUST publish span-level telemetry and Prometheus metrics (e.g., `trust_gate_status{gate=...,status=...}`, runtime gauges) with signed artifacts retained for at least three years. Observability dashboards and runbooks MUST link evidence artifacts (profiling trends, waiver cadence, parquet/CSV doctor alerts) to governing FR/SC IDs.

### VI. Performance Discipline
Performance targets are explicit & testable (memory reduction %, bootstrap overhead ratio, trust-gate runtime). Benchmarks live beside unit tests; failing a target is a regression unless waived with rationale and temporary threshold adjustment. Perf SLAs integrate Masters benchmarks with trust-gate timing thresholds. Profiling sprints and benchmark harnesses MUST remain scheduled, retain historical trends, and page reliability stewards when runtimes deviate by ≥10% from baseline.

### VII. Data Integrity & Causality Safety
No forward-looking data access in STRICT mode. Schema changes require explicit migration scripts + checksum and MUST bump a declared `schema_version` persisted with every record, manifest, and API payload. Validation & metrics reflect exact data & method parameters used. Tolerance profiles (e.g., `configs/trust_gates/tolerances/causality.yaml`) load deterministically; malformed or missing profiles fail closed. Retention policies are codified, enforced automatically, and respect pinned evidence with logged breaches. Data mutation post-hash calculation invalidates the run and must re-trigger pipeline. Trust gates enforce leak detection, universe stamping, accounting reconciliation, and tolerance SLA compliance before promotion.

### VIII. Documentation as Executable Interface
Schemas, heuristics, gating policies, error taxonomies, and API contracts are canonicalized in docs. Quickstarts MUST remain runnable. Each public module references its governing FR(s) and doc anchors. Docs for trust gates, retention policy, and waiver process MUST stay synchronized with configuration defaults.

### IX. Multi-Project Architecture (Dual Root)
Repository MUST maintain two explicit top-level roots:
```
alphaforge-brain/
	src/
	tests/
alphaforge-mind/
	src/
	tests/
```
Shared utilities (if any) live under `shared/` with pure, dependency-light modules. Cross-root code movement requires governance review. Brain never imports Mind; Mind consumes Brain via published interfaces (Python API boundary, REST/OpenAPI, or artifact schema). Version negotiation MUST be explicit (semantic version on contract layer). Integrity checks guard against drift.

### X. Contract Versioning & Backward Compatibility
Breaking changes to public Brain interfaces or artifact schemas MUST bump MAJOR version. Mind adopts new versions via upgrade path documented in migrations. Deprecations include sunset date & fallback strategy. Frontend contract verification artifacts (`zz_artifacts/frontend_contract.json`) are treated as release blockers when drift is detected.

### XI. Automated Governance & Waiver Discipline
Governance controls operate as self-enforcing systems. Configuration changes to trust-gate tolerances or retention policies MUST be schema-validated, signed, and logged in the change ledger before merge. Retention services enforce default budgets, respect manual pins, and audit every sweep; CLI pin/unpin actions persist auditable traces. Waiver programs run on a documented burn-down cadence—items exceeding 45 days escalate automatically, and no waiver survives beyond 60 days without executive approval. Runbooks map each mitigation, alert, and acceptance suite to the governing FR/SC identifiers so remediation remains traceable end to end.

## Multi-Project Architecture
1. Separation of Concerns: Brain focuses on computation, persistence, statistical engines; Mind focuses on visualization, orchestration, user workflows.
2. Deployment Independence: Either project can be deployed or tested in isolation (local dev harness, CI pipelines can run subset).
3. Contract Boundary: Only serialized artifacts (SQLite exports, JSON metrics, OpenAPI endpoints) cross the boundary.
4. Enforcement: Lint rule / script and runtime import hook ensure no forbidden imports; tasks include gating check.

## Transitional Architecture Migration
Current State (2025-09-23 scan): Single-root layout under `src/` with subpackages: api/, domain/, infra/, lib/, models/, services/. Tests mirror layered domains across `tests/` (integration, api, strategy, risk, etc.). Historical specs (001–004) reference a single backend; dual root not yet physically realized.

Target State: Physical separation into:
```
alphaforge-brain/ (existing backend code migrated here)
	src/
	tests/
alphaforge-mind/ (future UI + orchestration)
	src/
	tests/
shared/ (pure utilities only; optional & dependency-light)
```

Migration Commitments:
1. No new frontend (Mind) code is added inside current root; placeholder directory structure introduced in a dedicated migration PR.
2. Refactor Plan: (a) Create `alphaforge-brain/` and move existing `src/` & `tests/` contents; (b) Update import roots & tooling configs (mypy.ini, pytest paths, ruff includes); (c) Introduce stub `alphaforge-mind/` with README and placeholder package; (d) Add cross-root integrity CI script.
3. Backward Compatibility: API paths & package import names preserved via transitional shim (`src/` left temporarily with re-export modules) until internal imports are updated; shim removal scheduled after 2 minor releases.
4. Versioning: Migration PR must document any package name changes and bump MINOR (unless import paths break, then MAJOR).
5. Tracking: Feature 004 tasks to include architecture migration subtasks before introducing Mind-specific code.
6. Risk Mitigation: Determinism & tests executed after each directory move; hashing logic validated against pre-move snapshot.
7. Exit Criteria: All internal imports reference `alphaforge_brain` namespace; legacy `src/` root deleted; integrity script passes.

During the transition, Constitution rules treating dual roots as mandatory are interpreted as *planned enforcement* until Exit Criteria met; waivers recorded if interim deviations occur.

## Additional Constraints
- Storage: SQLite + Parquet (phase scope). No external DB without a ratified amendment.
- Dtypes: Enforced (timestamps int64 ns; price float32; volumes int64; derived numeric features float32) unless a precision benchmark justifies exception.
- Persistence Records: Every stored payload (SQLite rows, JSON artifacts, API documents) MUST declare `schema_version` aligned with the contracts catalog; migration scripts publish deterministic upgrade paths under `scripts/migrations/`.
- Hash Canonicalization: All JSON artifacts use sorted keys + UTF-8; content hash recorded & validated during replay.
- No Hidden Globals: Configuration MUST flow via explicit parameters or immutable config objects.
- Side-Effect Boundaries: IO restricted to persistence & dedicated adapters; models & statistical transforms remain pure.
- Coverage Floors: CI enforces ≥90% line, branch, integration, and function coverage; `quality_gates_summary.json` records failures with actionable diagnostics.
- Retention Policy: `configs/retention/policy.yaml` defines storage budgets; automated sweeps respect pins, log breaches, and require waivers for policy overrides.
- Trust Gate Artifacts: `trust_gate_report.json`, `ingest_vendor_metadata.json`, and Masters `perf_sla` records MUST persist under `zz_artifacts/` with SHA-256 hashes for compliance review.

## Workflow & Quality Gates
1. Lifecycle: Specify → Clarify → Plan → Tasks → Analyze → Implement → Validate → Release.
2. /analyze MUST show zero HIGH gaps before implementation begins.
3. Every PR includes: FR diff table, test diff summary, benchmark diff (where applicable), contract version impact.
4. Coverage Gate: CI enforces ≥90% line, branch, integration, and function coverage; quality gates fail closed with seeded negative-path fixtures.
5. Benchmarks: Guard overhead, observability overhead (<3%), memory reduction (≥ target), bootstrap runtime (≤1.2x IID). Failures block unless waiver file `WAIVERS.md` references FR & expiry. Benchmark harnesses publish historical trend artifacts and trigger alerts on ≥10% regressions.
6. Migrations: New/changed schemas require versioned migration + checksum update; unsupported drift = CI failure.
7. Contract Change Review: Any artifact schema or API change requires dual-project impact note (Brain producer, Mind consumer).
8. Cross-Root Integrity Enforcement: Static checks and runtime import guards ensure no Brain→Mind imports; shared utilities remain cycle-free.
9. Config Validation: CI schema-validates tolerance and retention YAML, verifies signed change-log entries, and blocks merges on configuration drift.
10. Trust Gate Governance: CI blocks when any gate fails without waiver; tolerance profiles missing/invalid fail closed. Waiver entries include remediation tasks, expiry ≤90 days, linkage to trust gate metrics dashboards, and participate in the burn-down cadence.

## Architecture Enforcement & Reviews
- Monthly Architecture Review: Validate modular boundaries, detect erosion.
- Complexity Thresholds: Module >400 LOC or function >75 LOC triggers review & potential decomposition issue.
- Cyclic Dependency Scan: CI script fails build on new cycles across packages.
- Validation Evidence: Trust gates and Masters validation artifacts MUST be attached to release candidates; absence is release blocker.
- Governance Dashboards: Weekly reviews confirm waiver cadence reports, retention sweeps, parquet/CSV doctor alerts, and profiling trend deltas remain within policy.

## Governance
- Amendment Types: MAJOR (remove/rename principles or break contract rules), MINOR (add principle/section), PATCH (clarification only).
- Amendment Process: Proposal doc → review → consensus approval → version bump commit.
- Violations: Logged as issues with label `constitution-violation`; remediation scheduled same iteration.
- Principle Waivers: Temporary waivers recorded in `WAIVERS.md` with expiry date (ISO) & justification.
- Waiver Cadence: Governance steward reviews waiver backlog weekly; items >45 days escalate automatically and >60 days require executive approval or closure.
- Contract Sunset: Deprecated interfaces MUST list removal version & replacement path.
- Config Ledger: Signed tolerance/retention change-log entries are mandatory for merges affecting `configs/trust_gates/` or `configs/retention/`; CI enforces signature + schema validation.
- Audit Trail: Release steward logs lineage/provenance attestations (dataset versions, waiver IDs, arbitration notes) in `docs/operations/trust_gates.md` and links to `WAIVERS.md` within 48 hours of each run. Runbook entries MUST map each mitigation to governing FR/SC IDs and the latest evidence artifact.

**Version**: 1.4.0 | **Ratified**: 2025-10-14 | **Last Amended**: 2025-10-14

---
## Governance Record (Architecture Migration)
On 2025-09-24, the repository completed the transition to a dual-root layout.
Reference status file: `alphaforge-brain/ARCH_MIGRATION_STATUS.md` (contains exit criteria and evidence).
CI enforces cross-root integrity via `scripts/ci/check_cross_root.py`. Strict-plus type/lint overlays are informational with ratchet on PRs.

Status file integrity: SHA-256 a0c86f61970a0fa7f6496dca36b37df51041d83efe098e220714c0dcd44543d0

---
## Governance Record (Phase H: Validation & Sign-Off)
On 2025-09-25, Phase H documentation and acceptance validation were completed for feature 004 (AlphaForge Brain Refinement).

Evidence:
- Validation Checklist: `specs/004-alphaforge-brain-refinement/validation-checklist.md`
- Acceptance Report: `specs/004-alphaforge-brain-refinement/ACCEPTANCE.md`
- CI Acceptance Suite: determinism replay + bootstrap CI width gate passing on default branch

Outcome:
- All Functional Requirements (FR-100–162, FR-150–158) have mapped tests and passing evidence.
- Documentation updated and linked from README.

Sign-off Recommendation: ACCEPT Phase H and maintain CI gates as merge blockers for determinism and width policy.
