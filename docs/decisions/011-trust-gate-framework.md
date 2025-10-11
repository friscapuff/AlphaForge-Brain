# Decision Record: Trust Gate Framework

- **Status**: Accepted (2025-10-11)
- **Participants**: Trust Gate Governance WG · Masters Validation WG · Mind Platform Team · Security Engineering Liaison
- **Related Work**: T030–T053 (Brain implementation, docs, governance), T050 (benchmark telemetry), T051 (runtime guard), T052 (documentation), T053 (governance), T061 (Mind dashboard panel)
- **Spec Reference**: [`specs/011-trust-gate-framework/spec.md`](../../specs/011-trust-gate-framework/spec.md)

## 1. Context

AlphaForge needed a deterministic pre-validation gate to enforce ingest integrity, causality, timezone normalization, universe completeness, equity reconciliation, and accounting balance before Masters validation executes. Earlier phases (Wave 3A/3B) delivered the suite orchestration, persistence, API surfaces, and Mind badges. Phase 4 added runtime guard rails and governance documentation. With Phase 5 we finalized:

1. **Security posture** for artifacts that include vendor metadata and signed reports.
2. **Operational visibility** surfaced via a Mind dashboard panel that consumes Prometheus metrics and emits global alerts.
3. **Governance/waiver workflow** tying runtime waivers to benchmark evidence and signed trust gate reports.

## 2. Decision

- Trust gate artifacts remain detached JSON + `.sig` files stored under `artifacts/trust_gates/reports/{run_id}` with access controls documented in `docs/security/trust_gate_metadata.md`.
- Prometheus remains the single source for live trust gate status; Mind consumes the `trust_gate_status`, `trust_gate_failures_total`, and `trust_gate_duration_seconds_*` series for both dashboard visualization (`TrustGatePanel`) and global alerting.
- Runtime guard compliance is enforced by `pytest alphaforge-brain/tests/perf/test_trust_gate_runtime.py` and backed by waivers that must include `trust_gate_report.json`, the detached signature, and the benchmark payload proving multiplier compliance.
- Governance policy (`docs/governance/retention_policy.md`) now mandates retention windows for reports, diagnostics, and waivers; `WAIVERS.md` prescribes attachments and baseline references for trust gate exemptions.
- Mind adds `/dashboard` route aggregating trust gate health while continuing to expose gate-by-gate detail via Trust Gate badges on the Backtest page.

## 3. Rationale

- **Determinism & Auditability**: Detached signatures + Key Vault-sourced keys guarantee tamper detection while keeping JSON parseable by downstream tooling.
- **Operational Clarity**: Prometheus metrics provide uniform ingestion for alerts; reusing them in Mind avoids separate health APIs and ensures alert parity with on-call dashboards.
- **Governance Enforcement**: Requiring benchmark payloads with waivers prevents runtime regressions from slipping through and ties to the documented 1.5× multiplier guardrail.
- **Security Alignment**: The dedicated security memo codifies classification, retention, and incident response, satisfying open question #1 from research about metadata protection.
- **UI Separation of Concerns**: A focused dashboard panel keeps high-signal trust gate status visible without cluttering the backtest workflow and allows future expansion (e.g., Masters SLA cards) under the same page.

## 4. Consequences & Follow-ups

- Trust gate metrics must continue to publish the documented Prometheus series; changes require updating the parser in `TrustGatePanel` and corresponding tests (`tests/unit/observability/trustGateMetrics.test.ts`).
- Security engineering will decide by **2025-10-20** whether vendor metadata requires column-level encryption (tracked in memo §7).
- Any new waiver template must include benchmark evidence; governance reviewers will reject entries missing `zz_artifacts/perf_latest.json` extracts.
- Mind's `/dashboard` route currently focuses on trust gates; follow-up tasks can layer Masters validation SLA widgets and ingest retry trends.
- Baseline regeneration tooling must emit signatures and metadata consistent with the memo; deviations trigger Sev2 response per memo §6.4.

## 5. Waivers & Exceptions

- No standing waivers. Temporary bypasses must cite signed trust gate report hashes and benchmark payloads per `WAIVERS.md`. Any waiver extending beyond 30 days requires Governance Council approval.

## 6. Alternatives Considered

| Option | Outcome |
|--------|---------|
| Embed trust gate report data inside manifests only | Bloats manifest, complicates signature rotation, and exposes vendor metadata wider than needed. |
| Build bespoke health API instead of parsing Prometheus | Duplicates scrape logic, diverges from existing observability stack, and delays alerts if API layer fails. |
| Treat runtime guard as informational (no waiver evidence) | Risks silent performance regressions; violates FR-211 guardrail acceptance criteria. |

## 7. Status Checklist

- Security memo published (`docs/security/trust_gate_metadata.md`) ✅
- Mind dashboard panel & Prometheus alert toast live (`/dashboard`, global toast) ✅
- Governance docs updated with waiver + retention guidance ✅
- Runtime guard test passing against current baseline ✅

Review this decision when Prometheus metric schema changes or when security mandates additional encryption for vendor metadata artifacts.
