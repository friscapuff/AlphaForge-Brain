<!--
Sync Impact Report
Version change: 1.0.0 -> 1.1.0 (MINOR: added explicit principle set, governance elaboration, no removals)
Modified principles: (template placeholders replaced with concrete definitions)
Added sections: Additional Constraints, Workflow & Quality Gates, General Governance details
Removed sections: None (template placeholders replaced)
Templates requiring updates: 
  .specify/templates/plan-template.md ✅ (principle references still valid: constitution check gates) 
  .specify/templates/spec-template.md ✅ (no mandatory section changes required) 
  .specify/templates/tasks-template.md ✅ (TDD & ordering align with Test-First principle) 
  README.md ⚠ (Add concise link/summary of principles) 
Deferred TODOs: None
-->

# AlphaForge Brain Constitution

## Core Principles

### 1. Deterministic Reproducibility (NON-NEGOTIABLE)
All backtest runs, artifacts, and hashes MUST be reproducible given identical inputs
(config + dataset snapshot). Data hashing, run hashing, and artifact manifests are
authoritative; any source of nondeterminism (time.now, randomness, external API drift)
MUST be isolated, seeded, or recorded. A run that cannot be reproduced by another
developer with the same commit and data is a defect.

### 2. Additive, Contract-First Evolution
Public schemas (OpenAPI, published JSON artifacts) evolve additively. Breaking field
removal or semantic mutation REQUIRES a major version proposal and migration plan.
Schema changes MUST be validated via automated diff + spectral lint. Every new contract
field MUST be documented and test-covered before merging.

### 3. Test-First Development Discipline
New behavior REQUIRES failing tests before implementation. Integration tests cover
end-to-end pipeline; unit tests for pure logic; contract tests for API responses;
regression (golden) tests for deterministic hashes/metrics. No feature flagged “done”
without green: mypy, ruff, pytest, spectral, bundle, benchmarks (when performance-impacted).

### 4. Data Integrity & Provenance Transparency
Every dataset ingested MUST surface: source path, calendar id, validation summary,
anomaly counters, content hash. No silent imputation of core OHLCV fields; invalid rows
are excluded with counters. Zero-volume rows retained with explicit flag. Provenance
metadata MUST propagate into manifests and API models.

### 5. Modular Domain Architecture
Core domains (data, features, strategy, risk, execution, run/orchestration) remain
loosely coupled via explicit interfaces/registries. Cross-domain imports are minimized
and cyclic dependencies forbidden. Abstractions must justify existence (single clear
responsibility) and include tests. Refactors that reduce coupling are prioritized.

### 6. Observability & Explainability
Structured logging (contextual key=value) required for ingestion anomalies, strategy
decisions, risk sizing outputs, and execution fills. Validation and metrics artifacts
are first-class explainability outputs; absence of explanatory context for a surprising
trade or sizing outcome is a defect.

### 7. Performance as a Guardrail (Not Premature Tuning)
Baseline ingestion + feature computation timings MUST be benchmarked (stored artifacts)
before optimizing. Optimizations REQUIRE: (1) proven regression or target, (2) pre and
post measurement, (3) no loss of determinism or clarity. Micro-optimizations without
measurable impact are rejected.

### 8. Extensibility Without Speculative Complexity
Designs MUST enable multi-symbol and future data provider expansion, but MAY NOT add
abstractions before a concrete second implementation is in scope—EXCEPT where doing so
later would cause breaking contract changes (e.g., symbol field in manifest). “YAGNI unless
retrofit is breaking” is enforced.

### 9. Single Source of Truth for Canonical State
Canonical dataset, feature registry, and run manifest each have exactly one authoritative
module. Duplication (shadow copies, repeated derivations) MUST be eliminated. Hash inputs
are explicitly enumerated; implicit environment-derived values are forbidden.

### 10. Tooling & Automation as Policy Enforcement
CI MUST gate merges on: tests, typing, linting, contract diff, spectral lint, reproducible
bundle, and (when present) benchmark threshold checks. Manual checklists are replaced by
scripted verifications where feasible. A broken CI gate is a release blocker.

## Additional Constraints
1. Python 3.11 is the mandated runtime until an explicit upgrade RFC accepted.
2. Only deterministic pure-Python or audited native deps (numpy, pandas) permitted; hidden
	randomness (e.g., multithread nondeterminism) MUST be sealed.
3. Docker image size growth >15% across MINOR versions REQUIRES justification.
4. Changelog fragments REQUIRED for any contract, principle, or manifest-affecting change.
5. Security: No outbound network calls in core backtest path; future API ingestion MUST be
	sandboxed and recorded.

## Workflow & Quality Gates
1. Branch naming: ###-short-feature (numeric prefix aligns artifacts).
2. Mandatory artifacts per feature before code: spec.md → plan.md → tasks.md.
3. No code merging before tasks.md exists and reflects current intent.
4. Quality gates (ALL green pre-merge): pytest, mypy strict, ruff, spectral, openapi bundle,
	changelog fragment, dataset validation tests.
5. Golden run regression revalidated if any risk, execution, or indicator code touched.
6. Benchmarks required to change or add performance-affecting code paths.

## Governance
1. Authority: This constitution supersedes ad-hoc style or undocumented practices.
2. Amendment Process:
	- Draft PR describing change + rationale + version bump classification.
	- Include diff summary + impact assessment + migration (if any).
	- MINOR bump for added principle/section; PATCH for clarifications; MAJOR for removals or
	  semantic redefinitions.
3. Versioning: Semantic (MAJOR.MINOR.PATCH). Stored in this file only; referenced by templates.
4. Compliance Review: Each feature plan includes a “Constitution Check” section referencing
	relevant principle IDs; reviewers MUST reject if non-compliant without justification.
5. Exceptions: Temporary deviations require an explicit TODO with expiry date; unresolved past
	expiry blocks release.
6. Source of Truth: Only this file defines principles—README provides summary link only.
7. Ratification: Initial ratification at 2025-07-01 (inferred); amendments logged via version bumps.

**Version**: 1.1.0 | **Ratified**: 2025-07-01 | **Last Amended**: 2025-09-21