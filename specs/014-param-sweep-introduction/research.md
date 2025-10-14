# Research – Param Sweep Introduction

## Decision 1: Deterministic Parameter Normalization
- **Decision**: Represent sweep parameters as a unified `ParameterDefinition` model that supports single values, ordered lists, and numeric ranges (start, stop, step) and expands into a sorted, deduplicated list of scalar values.
- **Rationale**: A single normalization path guarantees deterministic ordering, simplifies validation, and keeps the combination hash stable for governance evidence.
- **Alternatives Considered**:
  - Ad-hoc handling per strategy parameter — rejected because it scatters validation logic and risks divergent ordering.
  - Allowing free-form Python expressions — rejected due to determinism and security concerns.

## Decision 2: Sequential Sweep Execution with Guardrails
- **Decision**: Execute combinations sequentially (or via a deterministic, single-worker queue) and enforce the existing optimization combination cap before launching any runs.
- **Rationale**: Sequential execution preserves reproducibility, keeps trust-gate telemetry comparable, and respects existing resource envelopes; early cap checks avoid partial execution states.
- **Alternatives Considered**:
  - Parallel execution — deferred until governance approves reproducible multi-worker scheduling.
  - Per-run lazy cap enforcement — rejected because it can overrun storage/CPU before failing closed.

## Decision 3: Parent Sweep Manifest Schema
- **Decision**: Introduce a versioned parent manifest artifact capturing child run hashes, originating parameter values, aggregate telemetry, storage impact, and sweep metadata (timestamps, initiator, cap applied).
- **Rationale**: Consolidates lineage for audits, retention decisions, and downstream UI without altering child artifacts; aligns with Constitution Principle V for forensic auditability.
- **Alternatives Considered**:
  - Embedding sweep metadata inside each child manifest — rejected because it duplicates data and complicates single-run reuse.
  - Relying solely on database tables — rejected due to commitment to artifact-first governance workflows.

## Decision 4: Telemetry & Audit Signals
- **Decision**: Extend existing monitoring and audit logging to tag sweep submissions, cap rejections, and completion metrics (counts, durations, trust-gate latency aggregates) using the same log formats and Prometheus (or equivalent) exporters.
- **Rationale**: Reuses proven observability pathways, enabling dashboards to display sweep impact without bespoke collectors.
- **Alternatives Considered**:
  - Creating a new telemetry pipeline — rejected as unnecessary complexity.
  - Reporting only aggregated stats in parent manifest — rejected because real-time dashboards require streaming metrics.

## Decision 5: Documentation & Contract Strategy
- **Decision**: Update API contracts, quickstart guidance, and operational runbooks in lockstep with schema changes, emphasizing backend readiness while flagging future Mind UI integration.
- **Rationale**: Keeps Constitution Principle VIII satisfied and ensures downstream teams understand sweep semantics before UI wiring exists.
- **Alternatives Considered**:
  - Deferring documentation until UI work — rejected to avoid drift and onboarding gaps.

## Decision 6: Multi-Ticker Partitioning & Data-Cleansing Dependency
- **Decision**: Preserve per-ticker isolation by normalizing and executing sweeps independently for each ticker, while continuing to rely on the existing Brain data-cleansing services to deliver curated inputs prior to expansion. Partial successes (one ticker failing guardrails) capture waiver notes without blocking compliant tickers when governance approves.
- **Rationale**: Reusing trusted data-cleansing services avoids duplicating lineage tracking, and per-ticker isolation keeps manifests/audit trails straightforward for reviewers evaluating SC-005 parity and cap compliance.
- **Alternatives Considered**:
  - Building a new cleansing stage inside the sweep orchestrator — rejected due to duplication and drift risks.
  - Enforcing all-or-nothing ticker execution — rejected because governance may allow partial releases with waivers.
