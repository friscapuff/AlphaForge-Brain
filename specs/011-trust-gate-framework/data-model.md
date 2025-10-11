# Data Model: Trust Gate Framework

Feature: 011-trust-gate-framework
Spec: specs/011-trust-gate-framework/spec.md
Plan: specs/011-trust-gate-framework/plan.md
Research: specs/011-trust-gate-framework/research.md

## 1. Canonical Entities
| Entity | Purpose | Key Fields | Notes | Hash Participation |
|--------|---------|------------|-------|--------------------|
| `TrustGateSuite` | Configuration + execution metadata for full trust gate run. | `suite_id`, `run_id`, `config_hash`, `enabled_gates[]`, `tolerance_profile`, `executed_at`, `runtime_ms`, `version` | Stored in SQLite + manifest; drives reproducibility and waiver checks. | Config hash contributes to deterministic run hash; recorded in signed report. |
| `TrustGateResult` | Per-gate outcome capturing metrics, tolerances, artifacts, and diagnostics. | `result_id`, `suite_id`, `gate_type`, `status (pass/fail/warn)`, `metrics JSON`, `tolerance`, `artifact_path`, `correlation_id`, `waiver_ref?` | Persisted in `trust_gate_results` table and JSON artifact; referenced in Mind API. | Included in signed trust report SHA; optional inclusion in manifest hash if governance approves. |
| `GoldenRunBaseline` | Canonical determinism baseline for comparisons. | `baseline_id`, `config_digest`, `artifact_hashes JSON`, `dataset_hash`, `manifest_snapshot_path`, `version`, `signed_by` | Lives under `artifacts/trust_gates/baselines/`; referenced by trust suite. | Baseline signature hashed and compared; not part of run hash until adoption plan completed. |
| `LeakCatcherDataset` | Synthetic dataset metadata for causality audit. | `dataset_id`, `path`, `hash`, `bar_count`, `seed`, `fallback_dataset?`, `last_verified_at` | Maintained in metadata file for deterministic selection. | Hash recorded in trust report; dataset version mismatch fails gate. |
| `UniverseStamp` | Snapshot of expected universe membership. | `stamp_id`, `source`, `as_of`, `symbol_hash`, `symbol_count`, `missing_symbols[]?` | Stored in `contracts/trust_gates/universe_stamp.yml` and hashed; gate compares to ingest output. | Hash included in trust report; deviations flagged. |
| `TrustGateManifestExtension` | Manifest block summarizing trust suite for Mind/API consumption. | `status`, `executed_at`, `suite_version`, `gates[]` (gate, status, correlation_id, artifact_ref) | Embedded in run manifest; ensures downstream visibility. | Manifest hash extended with deterministic ordering. |

## 2. SQLite Schema Changes (Brain)
| Table | Change | Type | Backward Compatible? |
|-------|--------|------|----------------------|
| `trust_gate_suites` (new) | Columns: `suite_id TEXT PK`, `run_id TEXT`, `config_hash TEXT`, `enabled_gates TEXT`, `tolerance_profile TEXT`, `runtime_ms INTEGER`, `executed_at DATETIME`, `version INTEGER`, `signature TEXT` | New table managed via Alembic migration. | Yes, additive. |
| `trust_gate_results` (new) | Columns: `result_id TEXT PK`, `suite_id TEXT FK`, `gate_type TEXT`, `status TEXT`, `metrics JSON`, `tolerance JSON`, `artifact_path TEXT`, `correlation_id TEXT`, `waiver_ref TEXT`, `duration_ms INTEGER`, `details TEXT` | New table with JSON1 dependency. | Yes. |
| `runs` | Add nullable column `trust_gate_manifest JSON`. | Alembic migration extends manifest snapshot. | Yes; defaults to `NULL` for historical runs. |
| `baselines` (existing) | If present, add columns `baseline_type TEXT`, `trust_gate_version INTEGER`, `signature TEXT`. | Optional addition; can reuse `run_hash` table if available. | Yes; default `NULL`. |

## 3. Artifact Layout
```
artifacts/
  trust_gates/
    baselines/
      v1/
        golden_run_manifest.json
        artifact_hashes.json
        baseline.signature
    reports/
      {run_id}/
        trust_gate_report.json      # signed summary (FR-201, FR-209)
        gate_{type}_diagnostics.json
        ingest_vendor_metadata.json
        timezone_trace.parquet
```
- Reports include schema version, correlation IDs, and SHA256 of supporting artifacts.
- Diagnostics per gate stored in deterministic formats (JSON or Parquet) for reproducibility.
- Signatures stored as detached `.sig` files for governance review.

## 4. Manifest & API Contracts
| Contract | Change | Compatibility |
|----------|--------|---------------|
| Run Manifest (`manifests/{run}.json`) | Add `trust_gate` block with `status`, `suite_version`, `executed_at`, `gates[]` (name, status, artifact, correlation_id, waiver_ref?). | Additive; older manifests omit block. |
| Public API `GET /api/v1/runs/{id}` | Add `trust_gate` payload mirroring manifest structure + summary metrics (runtime, failing gates, tolerance profile). | Additive; Mind defaults to "Not Available" when absent. |
| SSE `run.update` (if present) | Stream trust gate completion event with `section="trust_gate"`. | Additive; clients ignore unknown sections. |
| Internal CLI output | `poetry run trust-gates` prints table with per-gate status, runtime, tolerance metadata, path to report. | Add CLI contract spec; exit code non-zero on failure. |

## 5. Mind Data Shapes
| Consumer | Expected Fields | Notes |
|----------|-----------------|-------|
| Trust Gate Status Badges | `trust_gate.status`, `gates[].status`, `gates[].name`, `gates[].waiver_ref`, `executed_at` | Display aggregated badge (Pass/Fail/Waived). |
| Diagnostics Detail View | `gates[].artifact`, `gates[].metrics`, `gates[].tolerance` | Provide popover with metrics like hash diffs, Sharpe epsilon, ingest hash mismatch list. |
| Timeline / Audit Log | `trust_gate.runtime_ms`, `trust_gate.version`, `trust_gate.correlation_id` | Combine with Masters validation to show overall readiness gating timeline. |
| Alerting Integration | Derived Prometheus metrics exported via API (`/metrics`). | Mind dashboards subscribe to metrics for active alerts. |

## 6. Configuration & Environment Inputs
| Setting | Default | Scope | Notes |
|---------|---------|-------|-------|
| `AF_TRUST_GATES_ENABLED` | true | Brain CLI/CI | Allows temporary bypass via waiver; log warning when false. |
| `AF_TRUST_GATES_ONLY` | empty | CLI flag `--only` to run subset (FR-213). | Accepts comma-separated gate names; CI forbids partial runs. |
| `AF_TRUST_GATES_TOLERANCE_PROFILE` | `institutional_default` | Determines thresholds for equity drift, accounting tolerance, timezone strictness. | Profiles stored under `configs/trust_gates/tolerances/*.yaml`. |
| `AF_TRUST_GATES_BASELINE_VERSION` | latest | Selects baseline directory for determinism comparison. | Governance increments version when baseline regenerated. |
| `AF_TRUST_GATES_VENDOR_RETRY_LIMIT` | 3 | Controls deterministic retry count for idempotent ingest. | Each retry schedule seeded by run configuration. |

## 7. Process Flow Summary
1. `poetry run trust-gates [--only ...]` loads configuration and resolves baseline + datasets.
2. Executor orchestrates gates sequentially (parallelizable groups) while capturing metrics, durations, and logs via structlog.
3. Results persisted to SQLite and serialized into `trust_gate_report.json`; signature appended using internal signing key.
4. Manifest extended with trust gate summary; API exposure updates automatically for Mind.
5. CI gating step blocks promotion if any gate status == `fail` without active waiver.

## 8. Backward Compatibility & Migration Plan
- Alembic migrations deliver new tables/columns; existing runs unaffected.
- Historical manifests remain untouched; Mind shows "Not Available" status.
- Baseline regeneration requires dedicated CLI (`poetry run trust-gates --refresh-baseline`) producing new `baseline.signature`; process documented in quickstart.
- Contract version `trust_gates.v1` introduced; future breaking changes require MAJOR bump and compatibility bridge.

## 9. Rejected Alternatives
| Alternative | Reason Rejected |
|-------------|-----------------|
| Embed trust gate report inside manifest only | Manifest would balloon; dedicated artifact allows detached signatures and archival. |
| Use event-driven ingestion to trigger gates | Adds complexity; CLI invocation keeps determinism and CI control. |
| Store diagnostics in MongoDB | Introduces new dependency; SQLite/JSON artifacts sufficient and deterministic. |
| Inline gating within Masters validation run | Risk of coupling and complicating failure triage; keep trust gates as prerequisite stage. |

## 10. Outstanding Questions
1. Should baselines support differential storage per strategy class (e.g., equities vs futures) or single global baseline? Awaiting data governance guidance.
2. Do we require encryption at rest for vendor metadata artifacts given retention policy? Pending decision from security.
