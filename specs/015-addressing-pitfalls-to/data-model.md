# Data Model: Operational Guardrail Remediation

## ValidationPerformanceReport
- **Fields**:
  - `report_id` (UUID) – unique identifier
  - `generated_at` (datetime, UTC)
  - `baseline_source` (string) – path/hash of baseline file
  - `bottlenecks` (list of `BottleneckEntry`)
  - `owner_assignments` (list of `OwnerAssignment`)
  - `recommendations` (list of string)
- **Relationships**:
  - Contains many `BottleneckEntry`
  - References `BenchmarkTrendAlert` records for supporting evidence
- **Validation Rules**:
  - Must include at least three bottleneck entries ranked by severity
  - `baseline_source` must match known baseline manifest

### BottleneckEntry
- `metric` (string)
- `current_mean_ms` (float)
- `baseline_mean_ms` (float)
- `delta_pct` (float)
- `confidence` (enum: high/medium/low)

### OwnerAssignment
- `fr_id` (string) – links to relevant Functional Requirement
- `owner` (string)
- `due_date` (date)

## BenchmarkTrendAlert
- **Fields**:
  - `alert_id` (UUID)
  - `generated_at` (datetime)
  - `metric_key` (string)
  - `baseline_ms` (float)
  - `observed_ms` (float)
  - `delta_pct` (float)
  - `ticket_url` (string)
  - `status` (enum: open, acknowledged, resolved)
- **Relationships**:
  - Links to `ValidationPerformanceReport` when alert triggered remediation
- **Validation Rules**:
  - `delta_pct` must be ≥10% to qualify
  - `ticket_url` must be present when status != open

## ConfigChangeLedger
- **Fields**:
  - `entry_id` (UUID)
  - `file_path` (string)
  - `schema_version` (string)
  - `checksum` (string)
  - `signed_by` (string)
  - `signed_at` (datetime)
  - `change_log_ref` (string)
- **Validation Rules**:
  - `checksum` must match current file contents
  - `schema_version` must exist in schema registry
  - Signature required for merge approval

## WaiverCadenceRecord
- **Fields**:
  - `waiver_id` (string)
  - `fr_ids` (list of string)
  - `opened_at` (date)
  - `age_days` (integer)
  - `escalation_status` (enum: normal, warning, escalated)
  - `next_action` (string)
- **Validation Rules**:
  - `age_days` recalculated daily
  - Escalation set to warning when `age_days` ≥ 45, escalated when ≥ 60

## SweepAcceptanceResult
- **Fields**:
  - `scenario_id` (string)
  - `ticker` (string)
  - `input_payload_hash` (string)
  - `expected_ordering` (list of string)
  - `observed_ordering` (list of string)
  - `cap_status` (enum: pass, hit)
  - `anomaly_flags` (list of string)
  - `runbook_link` (string)
- **Relationships**:
  - References fixture definitions in tests/fixtures
- **Validation Rules**:
  - Deterministic ordering required; mismatch triggers failure
  - Runbook link must exist for documentation traceability
