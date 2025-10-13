# Data Model: Testing Governance Hardening

## Entity Overview

| Entity | Description |
|--------|-------------|
| `ToleranceProfile` | Defines causality SLA thresholds, version metadata, and enforcement mode consumed by trust gates. |
| `ValidationGateResult` | Aggregates Masters validation outputs and produces gated status codes. |
| `PersistenceRecord` | Canonical payload wrapper stored in SQLite/JSON with schema versioning metadata. |
| `AccountingInvariantViolation` | Structured failure evidence when equity/accounting checks fail. |
| `RetentionPolicy` | Configuration driving automated retention sweeps, pin handling, and waivers. |
| `ImportGuardEvent` | Audit entry recorded when runtime cross-root import attempt occurs. |

## ToleranceProfile
- **Fields**:
  - `profile_id: str` – unique identifier (e.g., `causality-default`).
  - `schema_version: str` – semantic version of the tolerance schema definition.
  - `metrics: List[ToleranceMetric]` – each metric with `name`, `comparison`, `threshold`, `direction`, `window`.
  - `enforcement_mode: Literal["hard", "warn"]` – governs gate behavior.
  - `updated_at: datetime` – ISO8601 timestamp of last change.
- **Relationships**:
  - Referenced by trust gate runner when loading SLA file from `configs/trust_gates/tolerances/`.
- **Validation Rules**:
  - `threshold` must be numeric; `direction` ∈ {`above`, `below`}; `comparison` ∈ {`>` , `>=`, `<`, `<=`}.
- **Lifecycle**:
  - Version increments with SLA updates; previous versions archived for reproducibility.

## ValidationGateResult
- **Fields**:
  - `run_hash: str` – unique run identifier.
  - `permutation_p_value: float`
  - `cpcv_p_value: float`
  - `icc_width: float`
  - `status: Literal["PASSED", "FAILED_VALIDATION", "CAUTION"]`
  - `evidence_artifact: str` – path/URI to stored validation artifact.
  - `evaluated_at: datetime`
- **Relationships**:
  - Produced by Masters validation suite; consumed by orchestrator and retention logic.
- **Validation Rules**:
  - `status` must align with thresholds defined in research; `FAILED_VALIDATION` mandated when tolerances breached.
- **Lifecycle**:
  - Initial status `PASSED`/`CAUTION`; transitions to `FAILED_VALIDATION` immutable except via waiver record.

## PersistenceRecord
- **Fields**:
  - `record_id: str`
  - `schema_version: str` – matches JSON Schema definition in `contracts/persistence/`.
  - `payload: dict` – validated content for stored artifact.
  - `created_at: datetime`
  - `source_component: str` – e.g., `trust_gate`, `retention`, `masters`.
  - `validation_status: Literal["accepted", "rejected"]`
- **Relationships**:
  - Linked to migration history under `scripts/migrations/`.
- **Validation Rules**:
  - `payload` must validate against schema `schema_version`; rejects missing/unknown versions.
- **Lifecycle**:
  - On insert, validated and persisted; migrations update `schema_version` with deterministic scripts.

## AccountingInvariantViolation
- **Fields**:
  - `run_hash: str`
  - `trade_ids: List[str]`
  - `equity_delta: Decimal`
  - `cash: Decimal`
  - `unrealized_pnl: Decimal`
  - `fees: Decimal`
  - `tolerance: Decimal`
  - `detected_at: datetime`
- **Relationships**:
  - Generated when trust gate accounting module fails; attached to run manifest.
- **Validation Rules**:
  - `|cash + unrealized_pnl + fees - equity| <= tolerance` must hold; violation logs actual difference.

## RetentionPolicy
- **Fields**:
  - `policy_version: str`
  - `max_runs: int`
  - `per_strategy_top: int`
  - `pin_expiry_days: Optional[int]`
  - `waiver_required: bool`
  - `audit_log_path: str`
- **Relationships**:
  - Loaded by retention service; referenced by CLI operations.
- **Validation Rules**:
  - `max_runs >= per_strategy_top`; pins referencing expired waivers trigger breach log.
- **Lifecycle**:
  - Updated via configuration PR; version bump recorded in documentation.

## ImportGuardEvent
- **Fields**:
  - `event_id: str`
  - `timestamp: datetime`
  - `attempted_module: str`
  - `caller_module: str`
  - `stack_trace: str`
  - `environment: Literal["runtime", "cli", "test"]`
- **Relationships**:
  - Stored for audit review; optionally forwarded to logging sink.
- **Validation Rules**:
  - `attempted_module` must prefix `alphaforge-mind` when triggered; other values considered misconfiguration.
- **Lifecycle**:
  - Created whenever runtime guard intercepts invalid import; retention per logging policy.

## Coverage Signals
- **ToleranceProfile**: Serialize active `schema_version` and hash into run manifest; assert via trust gate telemetry tests that counters increment on breach.
- **ValidationGateResult**: Capture serialized payload samples in `zz_artifacts/trust_gates/validation_results.json` during regression suites.
- **PersistenceRecord**: Archive `schema_version` migration ledger entries alongside coverage XML to evidence FR-005/006 adherence.
- **AccountingInvariantViolation**: Provide fixture-driven JSON snapshots under `tests/data/governance/accounting/` to support negative test assertions.
- **RetentionPolicy**: Publish retention sweep logs with policy versions in `zz_artifacts/retention/retention_run.log` for every enforcement test.
- **ImportGuardEvent**: Export blocked import stack traces to `zz_artifacts/import_guard/events.json` during runtime guard tests for auditing.
