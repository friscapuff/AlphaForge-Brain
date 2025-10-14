# Data Model – Param Sweep Introduction

## ParameterDefinition
- **Purpose**: Canonical representation of a strategy parameter submitted for sweeps.
- **Fields**:
  - `name` (string, required) — strategy parameter key.
  - `mode` (enum: `single`, `list`, `range`) — indicates how values are supplied.
  - `value` (number|string, required when `mode=single`) — scalar to use for the parameter.
  - `values` (ordered list[number|string], required when `mode=list`) — explicit ordered set after validation.
  - `range` (object, required when `mode=range`) — `{start: number, stop: number, step: number}` using inclusive start / exclusive stop semantics; step must be >0.
  - `precision` (optional integer) — optional rounding precision applied during expansion (used for floats).
- **Validations**:
  - Exactly one of `value`, `values`, or `range` must be present.
  - Lists must be non-empty and contain unique values.
  - Ranges must produce at least one value after normalization; expanded values are rounded deterministically using `precision` (default 6 decimals).

## SweepCombination
- **Purpose**: Links a unique parameter set to an executed child run.
- **Fields**:
  - `combination_id` (string) — stable hash of sorted parameter-value pairs.
  - `parameters` (ordered list of `{name, value}`) — fully expanded scalar assignment for the run.
  - `run_hash` (string) — existing AlphaForge run hash for the child execution.
  - `status` (enum: `pending`, `running`, `succeeded`, `failed`, `skipped`) — execution lifecycle state.
  - `started_at` / `completed_at` (timestamp, optional) — lifecycle timing for telemetry aggregation.
  - `trust_gate_summary` (object, optional) — snapshot of validation outcomes (e.g., pass/fail, gating reason).
- **Validations**:
  - `parameters` must match the deterministic ordering recorded during expansion.
  - `run_hash` required for terminal states (`succeeded`, `failed`).

## SweepManifest
- **Purpose**: Parent artifact recording sweep lineage, configuration, and aggregate telemetry.
- **Fields**:
  - `schema_version` (string) — semantic version for governance.
  - `sweep_id` (string) — unique identifier for the sweep request.
  - `submitted_at` / `completed_at` (timestamp) — lifecycle markers.
  - `initiator` (string) — user or automation actor initiating the sweep.
  - `parameter_definitions` (list of `ParameterDefinition`) — normalized request payload.
  - `combinations` (list of `SweepCombination`) — child run lineage.
  - `tickers` (list of `TickerSweepManifest`) — per-ticker manifest descriptors (see below).
  - `combination_cap` (integer) — cap enforced at validation time.
  - `derived_metrics` (object) — aggregates such as total combinations, succeeded count, failed count, average duration, storage footprint.
  - `notes` (list of warning/error codes) — includes `OPTIMIZATION_SWEEP_LIMIT_HIT` or other governance signals.
  - `trust_gates` (object) — checkpoint evidence keyed by `payload_validation`, `normalization`, `orchestrator`, and `manifest`, each including `sanitized_parameters`, `data_quality_status`, `cap_status`, `latency_ms`, and reviewer notes.
- **Validations**:
  - `schema_version` must align with versioned contract in `contracts/persistence/`.
  - `combinations` entries must cover every expanded parameter assignment exactly once.
  - `tickers` list must include every ticker in the request and reference matching combinations by `combination_id` prefix.

## TickerSweepManifest
- **Purpose**: Captures per-ticker lineage, guardrail outcomes, and clean-data deltas relative to baseline single runs.
- **Fields**:
  - `ticker` (string) — symbol for this partition.
  - `combination_cap` (integer) — per-ticker cap applied at validation time.
  - `cap_status` (enum: `ok`, `hit`, `waived`) — guardrail verdict for the ticker.
  - `data_quality_status` (enum: `pass`, `fail`, `review`) — final clean-data verdict across checkpoints.
  - `variance_metrics` (object) — KPI deltas (PNL, drawdown, trade count) compared with baseline single-run artifacts, used to enforce SC-006 (≤0.1%).
  - `manifest_path` (string) — storage location `zz_artifacts/sweeps/<sweep_id>/<ticker>/manifest.json`.
  - `partial_execution_reason` (optional string) — describes why this ticker stopped early (e.g., `cap_hit`, `no_valid_combos`).
- **Validations**:
  - `variance_metrics` values must stay within configured thresholds (defaults align with SC-006) or flag `data_quality_status=review`.
  - `manifest_path` must exist whenever combinations executed for the ticker.

## SweepTelemetry
- **Purpose**: Logical view of metrics and audit signals emitted for monitoring.
- **Fields**:
  - `metric_name` (string) — e.g., `sweep_duration_ms`, `sweep_combinations_total`.
  - `labels` (object) — includes `sweep_id`, `ticker`, `checkpoint`, `cap_status`, `data_quality_status`, `initiator`.
  - `value` (number) — measurement value (duration, count, etc.).
  - `recorded_at` (timestamp) — emission time.
- **Validations**:
  - Label cardinality kept stable (no dynamic parameter names) to satisfy monitoring guardrails.
  - Emissions must occur at start/end of sweep plus on cap rejection and any data-quality failure, with latency recorded to validate SC-004 and checkpoint SLAs.
