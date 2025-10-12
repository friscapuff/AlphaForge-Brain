# Data Model – Test Hardening & Coverage Elevation

## QualityGateSummary
- **Description**: Canonical JSON artifact (`zz_artifacts/quality_gates_summary.json`) emitted by `run_quality_gates.py`.
- **Fields**:
  - `determinism`: object containing `exit_code`, optional `diff`, `baseline_hash`, `run_hash`.
  - `contract`: object with `committed_hash`, `regen_hash`, `drift`, optional `stderr`.
  - `migrations`: object with `exit_code`, `output`.
  - `memory`: object with `exit_code`, `within_cap`, `rss_bytes`, `cap_bytes`, optional `skipped`.
  - `cross_root`: object with `exit_code`, `output`.
  - `failures`: array of gate identifiers that failed.
  - `passed`: boolean summarizing success.
  - `generated_at`: ISO-8601 timestamp.
  - `version`: semantic version for the summary schema.
- **Relationships**: Consumed by CI dashboards and governance automation.

## CoverageThresholdPolicy
- **Description**: Machine-readable description of enforced coverage floors output during CI.
- **Fields**:
  - `target_line`, `target_branch`, `target_function`, `target_integration`: integers representing minimum percentages.
  - `module_overrides`: array of objects `{ module: str, min_line: int, min_branch: int }`.
  - `generated_at`: ISO-8601 timestamp.
  - `enforced_by`: identifier of CI job enforcing the policy.
- **Relationships**: Stored under `zz_artifacts/coverage_policy.json`; referenced by compliance docs and review tooling.

## DatasetManifest
- **Description**: Hash manifest for each canonical dataset used in fixtures (e.g., NVDA 5y CSV).
- **Fields**:
  - `dataset_name`: string identifier.
  - `path`: relative path to dataset file.
  - `sha256`: content hash.
  - `schema_signature`: ordered list of column definitions (name, dtype, nullable flag).
  - `row_count`: integer row total.
  - `generated_at`: ISO-8601 timestamp.
- **Relationships**: Validated at test setup before data-dependent suites execute; stored beside dataset in repo.

## PerfSlaRecord
- **Description**: Benchmark artifact produced by the perf gating job summarizing trust gate runtimes.
- **Fields**:
  - `suite`: identifier (e.g., `trust_gates`).
  - `mean_ms`, `p95_ms`: runtime statistics from latest run.
  - `baseline_mean_ms`: baseline reference.
  - `limit_multiplier`: multiplier applied to baseline (default 1.5).
  - `pass`: boolean indicating SLA compliance.
  - `run_id`: unique identifier for the benchmark execution.
  - `generated_at`: ISO-8601 timestamp.
- **Relationships**: Stored in `zz_artifacts/perf_latest.json` and cross-linked in governance docs.

## FrontendApiContractSnapshot
- **Description**: Versioned representation of the backend OpenAPI contract paired with the generated frontend client commit hash.
- **Fields**:
  - `spec_path`: relative path to the frozen OpenAPI JSON (`openapi.deref.json`).
  - `spec_sha256`: hash of the canonical OpenAPI payload.
  - `client_package`: npm package name for the generated TypeScript client.
  - `client_commit`: git SHA of the generated client artifact in `alphaforge-mind`.
  - `diff_summary`: list of breaking vs. additive changes detected by the diff job.
  - `verified_at`: ISO-8601 timestamp when contract verification completed.
  - `status`: enum (`clean`, `needs_regen`, `blocked`).
- **Relationships**: Produced by `scripts/contracts/verify_frontend_contract.py`, consumed by frontend CI to decide when to regenerate the client and run smoke tests.
