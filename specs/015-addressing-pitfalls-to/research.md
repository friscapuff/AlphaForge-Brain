# Research Findings: Operational Guardrail Remediation

## Decision 1: Benchmark Baseline Source
- **Decision**: Use `artifacts/perf_baseline.json` as the authoritative baseline for Masters validation metrics, cross-validated against the latest `zz_artifacts/perf_latest.json` snapshot.
- **Rationale**: The README documents this file as the canonical baseline, and SC-002 references it directly. Comparing against the latest snapshot ensures we detect drift while retaining historical provenance.
- **Alternatives Considered**:
  - Recompute baseline from scratch (rejected: unnecessary time, risks environmental drift).
  - Use ad-hoc metrics stored in Prometheus (rejected: lacks manifest linkage and determinism).

## Decision 2: Schema Validation Tooling
- **Decision**: Implement JSON Schema definitions for tolerance and retention YAML files, validated via Python script executed in CI (leveraging `jsonschema` library) plus git-signature check for accompanying change-log entry.
- **Rationale**: JSON Schema provides explicit structure enforcement; Python aligns with existing tooling and can integrate signature verification in one step.
- **Alternatives Considered**:
  - Rely on yamllint (rejected: syntax-only, no semantic validation).
  - Custom CI action in bash (rejected: harder to maintain, less expressive for schema evolution).

## Decision 3: Observability Integration
- **Decision**: Extend parquet doctor CLI to emit structured metrics to Prometheus and send alerts through existing Alertmanager routes with a unique alert label (e.g., `parquet_fallback=1`).
- **Rationale**: Prometheus/Alertmanager already power trust-gate alerts; reusing this stack ensures consistent routing and paging without reinventing notification channels.
- **Alternatives Considered**:
  - Direct Slack webhook in script (rejected: bypasses observability dashboards and paging rules).
  - Logging-only approach (rejected: no real-time alerting, contradicts SC-004).

## Decision 4: Waiver Cadence Automation
- **Decision**: Parse `WAIVERS.md` and governance tracker entries to compute waiver ages, producing a weekly JSON summary stored in `zz_artifacts/governance/waiver_cadence.json` and surfaced on dashboards.
- **Rationale**: The constitution already mandates waiver tracking in `WAIVERS.md`; generating structured data enables automated age checks and escalation triggers.
- **Alternatives Considered**:
  - Manual spreadsheet tracking (rejected: error-prone, undermines automation goals).
  - Database migration (rejected: overkill; existing markdown + JSON artifacts suffice).

## Decision 5: Sweep Acceptance Harness
- **Decision**: Build acceptance tests using deterministic fixtures under `alphaforge-brain/tests/sweeps/fixtures/`, mirroring sweep payloads with partial-cap and anomaly variants; compare outputs to frozen manifests in `tests/data/sweeps/expected/`.
- **Rationale**: Aligns with current testing conventions, ensures deterministic replay, and keeps expectations versioned.
- **Alternatives Considered**:
  - High-level integration test hitting live API (rejected: slower, introduces external dependencies).
  - Property-based tests without fixtures (rejected: harder to assert precise deterministic ordering).
