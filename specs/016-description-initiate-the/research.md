# Phase 0 Research — Enriching Journaling Detail, Quality, and Visualizations

## Decision 1: Benchmark window for journaling validation
- **Decision**: Anchor journaling performance targets to current trust-gate and validation spans, budgeting ≤5 s end-to-end with ≤3 % runtime overhead relative to the 40 s benchmarked run.
- **Rationale**: `zz_artifacts/perf_latest.json` (2025-10-14) records `trust_gate_total_mean_ms` ≈15 ms and `validation_total_mean_ms` ≈557 ms for a representative run; `docs/decisions/validation_schema_v2.md` notes prior Masters rollouts observed 1 543 ms validation spans. Setting the journaling budget at 5 s (including new artifact validation) keeps us well inside the constitutional trust-gate SLA (5 000 ms threshold in `services/trust_gates/suite_service.py`) while leaving headroom for heavier strategies.
- **Alternatives considered**:
  1. **Fixed 500 ms ceiling** — rejected: too tight for richer artifact hashing and would immediately fail existing regression data.
  2. **No explicit budget** — rejected: violates Constitution VI and XI requirements for measurable guardrails.

## Decision 2: Retention policy touchpoints for enriched artifacts
- **Decision**: Treat enriched journaling payloads as “full run” artifacts governed by `max_runs=60`, `per_strategy_top=6`, pin expiries ≤90 days, and mandatory waiver logging, using the same audit paths as existing trust-gate outputs.
- **Rationale**: `configs/retention/policy.yaml` (version 2025.10.13) and `domain/run/retention_policy.py` enforce 60 run history, per-strategy top ranks, and waiver requirements. `docs/operations/trust_gates.md` documents breach logging via `zz_artifacts/retention_breaches.log` and CLI audit trails. Aligning journaling assets with these limits avoids new policy branches and preserves automation evidence.
- **Alternatives considered**:
  1. **Dedicated journaling retention budget** — rejected for Phase 016; would require policy amendments and new audit scripts.
  2. **Manifest-only demotion** — dismissed because researchers need full payloads for expectancy and checklist analysis.

## Decision 3: Throughput and trade-volume expectations
- **Decision**: Plan for bursts of up to eight trust-gate evaluations per minute and trade counts up to ~50 fills per run when sizing storage and batching journaling aggregates.
- **Rationale**: Analysis of `zz_artifacts/governance/trust_gates_latency.jsonl` shows a peak of 8 suite executions within a single minute (2025-10-13 00:35). Parsing `artifacts/*/summary.json` reveals observed trade counts ranging from 0 to 52 (median ≈22) across 920 samples. Designing aggregations and retention sweeps for ≥8 parallel run completions prevents backlogs during nightly sweeps and supports multi-strategy experiments.
- **Alternatives considered**:
  1. **Assume sequential runs only** — rejected: contradicted by observed audit bursts.
  2. **Over-provision for 20 concurrent runs** — postponed until Mind orchestration introduces wider fan-out; current evidence does not justify the cost.

## Decision 4: Deterministic hashing & schema evolution technique
- **Decision**: Reuse `services.hashing.validation_signature.hash_canonical` patterns (sorted keys, stable list ordering, manifesto normalization) for new journaling payload hashes and emit schema-versioned change logs.
- **Rationale**: Existing validation hashing normalizes nested structures, sorts permutation segments, and strips recursive fields before hashing. Applying the same pattern to journaling ensures deterministic hashes and smooth integration into trust-gate manifests (Constitution VII & X). Versioned change logs keep Mind consumers backwards-compatible.
- **Alternatives considered**:
  1. **Plain `json.dumps` without sorting** — rejected: ordering drift would break determinism.
  2. **External hashing dependency** — unnecessary; in-repo canonical hashing already audited.

## Decision 5: Trust-gate integration pattern
- **Decision**: Extend `services.trust_gates.suite_service.TrustGateSuiteService` to validate journaling completeness, emitting Prometheus metrics and latency logs alongside existing gates instead of creating a separate suite.
- **Rationale**: The suite service already logs runtime (threshold 5 000 ms) and appends audit entries to `zz_artifacts/governance/trust_gates_latency.jsonl`. Augmenting the existing suite keeps governance dashboards intact, ensures fail-closed behaviour, and leverages tolerance profile loading (`load_tolerance_profile`).
- **Alternatives considered**:
  1. **Standalone journaling gate runner** — would duplicate telemetry plumbing and weaken governance cohesion.
  2. **Post-processing check outside trust gates** — would violate Constitution II (fail-closed) by allowing incomplete payloads to slip past release blockers.
