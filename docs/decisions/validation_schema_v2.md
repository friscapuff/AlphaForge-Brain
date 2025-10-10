# Decision Record: Validation Schema v2

- **Status**: Accepted (2025-10-10)
- **Participants**: Validation Working Group (Brain platform, Data, Governance)
- **Related Work**: T035 (migration), T036 (hashing), T041 (SLA guard rails), T042 (this record)
- **Spec Reference**: [`specs/010-description-integrate-masters/spec.md`](../../specs/010-description-integrate-masters/spec.md)

## 1. Context

Masters integration requires expanding persistence for permutation p-values, Sharpe bias diagnostics, CPCV leakage scores, and execution realism outcomes. Prior schema stored validation outputs across multiple tables (`validation`, `phase_metrics`, ad hoc JSON in manifests). Introducing Masters modules surfaced two conflicting proposals:

1. **Split-per-module tables** – create dedicated tables for permutation segments, bias adjustments, cross-validation folds, and realism checks.
2. **Unified validation record** – evolve the existing `validation_results` table (Alembic revision `20251010001`) with a type discriminator and JSON payload per module.

Concurrency constraints (CI runs + replay tooling) and deterministic hashing requirements limited how many migrations we could stage. We also needed guard rails (FR-015) to measure validation runtime per Masters module without duplicating persistence writes.

Separately, Masters methodology standardises the default purge span for purged K-Fold / CPCV as the max of **30 calendar days** or the strategy lookback horizon. This assumption was clarified during T001/T009 design sign-off and needed to be locked for governance parity.

## 2. Decision

We adopted the **unified validation record** approach and codified the purge-span rule:

- `validation_results` now stores every Masters module outcome with a `validation_type` enum (`permutation`, `bias_adjustment`, `cross_validation`, `execution_realism`, `aggregate`). Module-specific metrics (p-values, effect sizes, leakage scores, guidance) reside in the JSON1-backed `metadata` column.
- Manifest schema v2 references these rows directly, keeping historical runs neutral via nullable columns.
- Purge-span default is baked into `ValidationRuntimeConfig`: `purge_span = max(30 days, strategy lookback horizon)`. CPCV fallbacks document the computed embargo window in persistence and manifests.
- FR-015 guard rails rely on `phase_metrics` spans with prefix `validation.*`; scripts like `scripts/bench/perf_run.py` consume these timings to enforce SLA thresholds.

## 3. Rationale

- **Operational Simplicity**: A single table avoids cross-table joins during `GET /runs/{id}` serialization and keeps Alembic migrations additive. Replay tooling (T036) only rehydrates one logical source of truth.
- **Extensibility**: JSON1 metadata allows appending fields for future modules (e.g., alternative realism checks) without further migrations, while the discriminator keeps analytics simple.
- **Determinism**: Deterministic hashing (manifest + validation signature) operates on a consistent sorted set of rows, eliminating ordering drift that multiple tables would introduce.
- **Performance Guard Rails**: Recording validation spans alongside module metadata enables benchmark scripts (T041) to fetch per-stage durations for SLA enforcement without additional persistence writes.
- **Governance Alignment**: Hard-coding the 30-day-or-lookback purge span matches Masters methodology and ensures compliance team reviews a single documented rule.

## 4. Consequences & Follow-ups

- Existing queries reading from `validation` must migrate to the new `validation_results` view helpers; legacy columns remain nullable for back-compat but will be deprecated after the v2 rollout.
- Property tests (planned T043) should assert that module metadata serializes reproducibly to guard against schema drift in the JSON payloads.
- Mind adapters rely on the unified payload; ensure contract snapshots stay in sync when additional module fields are introduced.
- Governance artefacts (retention policy, operations backfill guide) must reference this decision when documenting purge-span enforcement and schema evolution (tracked under T046/T047).
- Latest SLA benchmark (2025-10-11) recorded `validation.total` mean at 1543 ms versus the 34 ms guard limit, so performance tuning remains open; monitor subsequent runs and document remediation in follow-up tasks.

## 5. Alternatives Considered

| Option | Outcome |
|--------|---------|
| Dedicated tables per module | Higher migration surface, more joins in API serializers, complicates deterministic hashing. |
| Keep legacy validation table untouched | Fails to meet FR-001/FR-004 requirements; no place to store Masters outputs or new metadata. |
| Configurable purge-span via UI | Defers governance alignment; increases risk of accidental leakage by end users. |

## 6. Status Checks

- Alembic revision `20251010001_validation_schema_v2` deployed with JSON1 guard ✅
- Manifest writer emits `validation_schema_version = 2` and embeds module metadata ✅
- Bench harness (`scripts/bench/perf_run.py`) captures validation spans; most recent run flagged an SLA breach for `validation.total` mean 1543 ms > 34 ms limit ✅
- Purge-span default logged in manifest + metadata for audit ✅

No further action required; revisit only if Masters runtime exceeds SLA thresholds or governance revises purge-span policy.
