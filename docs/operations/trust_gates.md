# Trust Gate Operations Guide

**Last Updated**: 2025-10-13
**Owner**: Release Steward (AlphaForge Brain)

This guide operationalizes the trust gate framework across ingest → transform → emit, ensuring compliance with constitutional principles and the newly introduced non-functional requirements.

## 1. Artifact Retention & Security Policy

| Artifact | Minimum Retention | Storage Requirements | Integrity Actions |
|----------|-------------------|----------------------|-------------------|
| `trust_gate_report.json` (signed) | 3 years | AES-256 encrypted disk or encrypted S3/GCS bucket | Quarterly re-hash rotation logged in §5 |
| `ingest_vendor_metadata.json`, retry traces | 18 months (540 days) | Same encryption standard as above | Monthly checksum verification |
| Waiver records referencing trust gates (`WAIVERS.md`, attachments) | Active + 90-day expiry window | Primary repo (git) + cold storage copy within 24 hours | Expiry audit during weekly governance review |
| Baseline & leak-catcher datasets | Per data governance policy (min 3 years) | Immutable artifact store (hash-addressed) | Regenerate with signed approval |

**Retention Automation Defaults**

- The canonical retention policy is versioned at `configs/retention/policy.yaml` (current version: `2025.10.13`). Use `poetry run alphaforge-brain retention policy inspect` to review limits and waiver requirements before a sweep.
- Runtime breaches append structured JSON lines to `zz_artifacts/retention_breaches.log` and emit the `governance_event_total{event_type="retention_breach",reason=*}` Prometheus counter. Investigate and file a waiver before promoting affected runs.
- Pin and unpin sensitive runs via `poetry run alphaforge-brain retention pin --run-hash <hash> --waiver-id <id>` and `poetry run alphaforge-brain retention unpin --run-hash <hash>`; each action records an audit event in `GOVERNANCE_AUDIT_PATH`.

**Encryption Standard**
- Local storage: BitLocker or LUKS with AES-256.
- Cloud storage: S3/GCS buckets with default SSE-KMS or CMEK enforcing AES-256.
- Key rotation cadence: every 6 months (aligned with operations security playbook).

## 2. Performance Guardrails & Tolerance Profile

### 2.1 Runtime Limits (FR-211)

- **Benchmark harness**: `poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json`
   - The harness now emits `trust_gates.stages.trust_suite.total.mean_ms`, per-gate spans, and a top-level `perf_sla` record covering `mean_ms`, `p95_ms`, `baseline_mean_ms`, the enforced `limit_multiplier`, `pass`, `run_id`, and `generated_at`.
   - Raw iterations and stage breakdown live under the `trust_gates` key in the JSON payload (and the optional output file if `--output` is supplied). Override the SLA guard locally with `--limit-multiplier <value>` when running exploratory experiments.
   - Validate the CI wrapper without tripping the 90 % coverage floor by running `poetry run pytest --no-cov tests/ci/test_perf_gates_script.py`.
   - PerfSlaRecord schema (persisted at `perf_sla`):

     | Field | Type | Description |
     |-------|------|-------------|
     | `suite` | `str` | Source suite emitting the SLA verdict (`trust_gates`). |
     | `mean_ms` | `float` | Average runtime observed for the suite. |
     | `p95_ms` | `float` | 95th percentile runtime across measured iterations. |
     | `baseline_mean_ms` | `float` | Baseline mean from `artifacts/perf_baseline.json` when present. |
     | `limit_multiplier` | `float` | Guardrail multiplier applied to the baseline (defaults to **1.5×**). |
     | `pass` | `bool` | `true` when the run respected the computed SLA limit. |
     | `run_id` | `str` | Hash or generated identifier for the benchmarked run. |
     | `generated_at` | `str` | UTC ISO-8601 timestamp describing when the record was emitted. |
- **Baseline source**: `artifacts/perf_baseline.json` captures the current Masters validation mean runtime (`summary.mean_ms`).
- **Guardrail**: `trust_suite.total` must remain ≤ 1.5× the baseline mean.
   - Current baseline mean = **28.49 ms**, so the suite limit is **≤ 42.73 ms**.
   - CI enforces the guard via `tests/perf/test_trust_gate_runtime.py`; failures require a documented waiver plus baseline refresh plan.
- **Interpretation**: If the mean exceeds the limit, investigate recent gate changes, regenerate baselines if intentional, and update tolerances/waivers before promoting the run.

### 2.2 Gate Threshold Cheat Sheet (Institutional Default)

| Gate | Thresholds |
|------|------------|
| Golden Run Determinism | Manifest and artifact hashes must match baseline; SQLite digest required; baseline version mismatches are not permitted. |
| Causality Guardrails | Leakage score ≤ 0.05, equity drift ≤ 1×10⁻⁶, Sharpe Ratio floor ≥ 0.0. |
| Ingest Idempotency | Hash delta = 0; schema version parity enforced; ≤ 3 retry attempts; row counts must match baseline snapshot. |
| Timezone Normalization | Storage must be UTC; offset 0 s; ambiguous transitions buffered 5 min; DST gap ≤ 60 s; leap seconds allowed. |
| Universe Stamp | Missing symbols fail the suite; additional symbols warned but not blocked; symbol delta limit = 0. |
| Equity Reconciliation | Absolute currency drift ≤ 0.01; relative drift ≤ 5 bps; corporate-action metadata required. |
| Accounting Balance | Absolute currency drift ≤ 0.01; relative drift ≤ 5 bps; ledger precision 6 decimals with bankers rounding. |

Refer to `configs/trust_gates/tolerances/institutional_default.yaml` for the authoritative schema and future profile revisions.

### 2.3 Telemetry & Dashboard Feed (FR-010)

- `scripts/ci/run_perf_gates.py` emits a Prometheus snapshot at `zz_artifacts/trust_gate_metrics.prom` on every scheduled and PR run. The snapshot includes:
   - `trust_gate_status{gate=...,status=...}` gauges (1 when the status was observed during the most recent suite execution).
   - `trust_gate_duration_ms{gate="<name>"}` and `trust_gate_duration_ratio{gate="<name>"}` for mean runtime and share vs suite total.
   - `trust_gate_suite_runtime_ms`, `trust_gate_suite_pass`, and `trust_gate_suite_limit_ms` to chart SLA drift.
   - `validation_suite_duration_ms` mirroring the Masters validation wall-clock mean (ms).
- Dashboards should scrape/push this artifact so observability surfaces trust-gate regressions in real time. When the file is missing, rerun `poetry run python scripts/ci/run_perf_gates.py` locally and resolve any dependency errors before promoting.
- Sweep telemetry emits complementary metrics alongside trust-gate outputs:
   - `sweep_checkpoint_latency_seconds{sweep_id=...,ticker=...,checkpoint=...,cap_status=...,data_quality_status=...}` histograms map each checkpoint to its latency budget.
   - `sweep_combinations_total{...}` counts executed combinations per checkpoint, enforcing deterministic evidence.
   - `sweep_guardrail_events_total{reason="combination_cap",...}` records cap hits and future waiver justifications.

### 2.4 Parquet/CSV Fallback Alerting (FR-004)

- The cache doctor CLI (`poetry run python -m infra.cache.doctor --root cache/candles --alerts zz_artifacts/governance/cache_doctor_alerts.jsonl`) now emits the Prometheus gauge `cache_parquet_fallback_active{root="<cache_root>"}`.
- Alertmanager rule `configs/prometheus/alert_rules/parquet_fallback.yaml` raises `ParquetFallbackDetected` after five continuous minutes with one or more CSV fallback files. The rule is tagged `severity=page` and routes through the same on-call escalation as trust-gate regressions.
- Dashboards should chart the gauge (expect steady state = 0) and expose the most recent fallback paths from `zz_artifacts/governance/cache_doctor_alerts.jsonl`.
- Automation triggers the doctor on nightly benchmark runs; operators may run it ad-hoc before validating sweeps when storage health is in question.
- When an alert fires, follow the [Parquet Fallback Response runbook](#parquet-fallback-response) and record the incident in the governance tracker.

## 3. Governance Logging Workflow (Solo & Team)

1. After every trust gate run, execute the automation script (see §4) within 48 hours.
2. Script appends a lineage attestation entry to this document (appendix) including:
   - Run ID, execution timestamp, tolerance profile.
   - Vendor versions, dataset hashes, baseline version.
   - Waiver references (ID, expiry) or `none`.
   - Notes on tolerance arbitration events.
3. If waivers exist, ensure cold-storage copy is created.<br>
   - Default location: `artifacts/trust_gates/waivers_cold/` with encrypted zip per waiver.
4. During weekly review, confirm pending entries resolved before expiry.
5. Log completion of the quarterly hash rotation with script output hash digests.

## 4. Automation Scripts

### 4.1 `scripts/operations/log_trust_gate_run.py`

Purpose: Automate the attestation workflow, enforce retention timelines, and perform cold-storage copies.

*Responsibilities*
- Parse run metadata (`trust_gate_report.json`, manifest extension) to capture lineage fields.
- Validate tolerance arbitration logs (from structlog or report diagnostics).
- Append Markdown entry to §6 (Automation Appendix) in this document.
- Ensure `WAIVERS.md` entries have expiry ≤90 days; warn otherwise.
- Compress and encrypt waiver attachments, copying them to `artifacts/trust_gates/waivers_cold/` with timestamped filename.
- Emit structured log for observability: `trust_gate_run_logged` with attestation slug.

### 4.2 `scripts/operations/rotate_trust_gate_hashes.py`

Purpose: Re-validate signed artifacts quarterly and capture diff evidence.

*Responsibilities*
- Iterate over retained `trust_gate_report.json` files.
- Recompute SHA256 signatures and compare against stored values.
- Record results in `docs/operations/trust_gates.md` §6.
- Emit metrics via Prometheus push gateway (optional) for dashboarding.

## 5. Runbook

### Routine Run (Per Trust Gate Execution)
1. Ensure trust gate suite completed (`poetry run trust-gates`).
2. Run logging script (include operator handle and optional waiver attachments):
   ```powershell
   poetry run python scripts/operations/log_trust_gate_run.py --run-id <RUN_ID> --operator <YOU> [--waiver-attachment path/to/waiver.pdf]
   ```
3. Review appended entry in this document; confirm encryption + cold storage steps succeeded.
4. If tolerances were arbitrated, ensure reason and waiver details included.
5. Update `WAIVERS.md` if any new waivers issued; reconfirm expiries and attach the Prometheus snapshot reference (`zz_artifacts/trust_gate_metrics.prom`).

### Parquet Fallback Response

1. Acknowledge the `ParquetFallbackDetected` page within five minutes (SC-004). Confirm the alert metadata in Alertmanager for the affected cache root.
2. Run the diagnostic locally to capture fresh evidence:
   ```powershell
   poetry run python -m infra.cache.doctor --root cache/candles --alerts zz_artifacts/governance/cache_doctor_alerts.jsonl
   ```
   Review the alert line items for the fallback files and sizes.
3. Inspect recent parquet writes for the identified root. Typical causes include schema drift, Arrow writer failures, or disk saturation. Remediate and rerun the doctor CLI until `cache_parquet_fallback_active` returns to 0.
4. File or update the governance incident ticket referenced by the benchmark alert automation; attach remediation notes and affected run hashes.
5. Once resolved, annotate the cache doctor alert log with the resolution timestamp and ensure dashboards show the gauge back at 0. Close the alert in Alertmanager and notify the release steward during the next operations standup.

### Runtime Import Guard Troubleshooting *(add before 2025-10-31 per constitution XI)*

The runtime import hook and lint rules enforce the dual-root boundary. When either surface a violation, act immediately to preserve determinism and governance guarantees.

1. **Detect & Classify**
   - Runtime failures raise `RuntimeImportGuardError` (Brain importing Mind) or `CrossRootImportViolation`. Capture the full traceback and offending module path.
   - Lint failures originate from `scripts/ci/check_cross_root.py` or Ruff plugin `AFB999` (placeholder). Record the file + import statement.
   - File an incident ticket with severity `guardrail` and link the failure evidence.
2. **Verify Guard Configuration**
   - Ensure `ALPHAFORGE_RUNTIME_IMPORT_GUARD=1` (default via `.env.ci`). For local repro run:
     ```powershell
     $env:ALPHAFORGE_RUNTIME_IMPORT_GUARD = "1"
     poetry run pytest tests/imports/test_cross_root_guard_runtime.py
     ```
   - Re-run the static check: `poetry run python scripts/ci/check_cross_root.py --fail-on-warning`.
3. **Remediate Offending Import**
   - Relocate shared logic into `shared/` (must remain dependency-light) or publish an explicit contract (OpenAPI/artifact).
   - Update callers to consume the contract/utility. Verify no residual imports remain across the roots.
4. **Re-run Guards & Document**
   - Execute the runtime test again plus the lint script. Confirm zero violations and update the incident ticket with remediation summary.
   - Append a note to `docs/operations/trust_gates.md` Automation Appendix if artifacts were regenerated and link any waivers if temporary exceptions were required.
5. **Escalation Path**
   - If the guard keeps firing or requires a temporary waiver, record it in `WAIVERS.md` with expiry ≤45 days and notify architecture reviewers at the weekly governance standup.
   - For third-party dependencies causing dynamic imports, coordinate with Platform Engineering to sandbox or shim the behavior before re-enabling the guard.

Checklist before closing the incident:
- [ ] Static check passes (`scripts/ci/check_cross_root.py`).
- [ ] Runtime test passes (`tests/imports/test_cross_root_guard_runtime.py`).
- [ ] No waivers older than 45 days remain open for the guard.
- [ ] Contract documentation (README, quickstart, runbook) references any new integration paths.

### Quarterly Maintenance
1. Execute hash rotation script:
   ```powershell
   poetry run python scripts/operations/rotate_trust_gate_hashes.py --since 90d
   ```
2. Address any mismatched hashes (investigate integrity breach, regenerate artifact if necessary).
3. Record the reported hash values in §6 (append manual note or run logging script in dry-run mode) with operator signature.

### Sweep Anomaly Investigation

Scenario **`anomaly-ordering-drift`** from the acceptance suite provides the canonical evidence trail for unexpected ordering variance. When Alertmanager raises an ordering anomaly or the acceptance suite flags `ordering_mismatch`, take the following steps:

1. Review `zz_artifacts/governance/sweep_acceptance.json` (generated by `services.orchestration.sweep_acceptance.run_acceptance_suite`) to confirm the anomaly surfaced in the governance ledger.
2. Cross-check the manifest ordering in the related sweep directory; compare against the `expected_ordering` captured in the acceptance artifact.
3. File an investigation ticket referencing this runbook section and cite FR-006/SC-006 compliance, noting whether the variance was intentional (baseline refresh) or a regression requiring rollback.
4. Update `docs/operations/validation_backfill.md#deterministic-ordering` once remediation is complete so the baseline scenario remains trustworthy.

### Deterministic Ordering

The acceptance suite's **`deterministic-baseline-validation`** scenario should remain anomaly-free. After any trust gate or sweep orchestration change:

- Re-run the acceptance suite:
   ```powershell
   poetry run pytest alphaforge-brain/tests/sweeps/test_acceptance.py
   poetry run python - <<'PY'
   from services.orchestration import sweep_acceptance

   sweep_acceptance.run_acceptance_suite()
   PY
   ```
- Attach the refreshed `sweep_acceptance.json` to the governance review deck and document the confirmation in this section.
- If anomaly flags appear, halt sweep promotions until parity with `expected_ordering` is restored.

## 6. Automation Appendix (Attestations)
This section is auto-appended by the logging script.


## 7. Sweep Prerequisites (Param Sweep Introduction)

Use this checklist before authorizing sweep runs governed by `/specs/014-param-sweep-introduction/`.

1. **Governance Evidence Ready**
   - Confirm all sweep checklists are complete:
     - `specs/014-param-sweep-introduction/checklists/data-governance.md`
     - `specs/014-param-sweep-introduction/checklists/multi-ticker.md`
     - `specs/014-param-sweep-introduction/checklists/requirements.md`
   - Review the `/specs/014-param-sweep-introduction/quickstart.md` governance section to ensure telemetry expectations (`cap_status`, `data_quality_status`, latency metrics) are understood.
2. **Environment Guardrails Set**
   - Validate `AF_OPTIMIZATION_MAX_COMBINATIONS` matches the intended sweep cap for the run.
   - Ensure the Brain data-cleansing services are healthy (Decision 6 in `research.md`); sweeps rely on curated inputs.
3. **Payload & Fixture Prep**
   - Use the canonical fixture `alphaforge-brain/tests/data/sweeps/dual_sma.json` as a template when crafting new payloads, adjusting tickers/overrides as needed.
   - For multi-ticker requests, document any per-ticker waivers in `WAIVERS.md` ahead of execution.
4. **Trust-Gate Checkpoints**
   - Verify operators know the four sweep checkpoints (`payload_validation`, `normalization`, `orchestrator`, `manifest`) and where manifests store `sanitized_parameters`, `cap_status`, and `data_quality_status` fields (see Spec §Clean Data Propagation Flow).
   - Confirm monitoring dashboards (Prometheus) are scraping sweep telemetry before initiating the run. Tail `zz_artifacts/governance_audit.log` for `sweep.checkpoint` and `sweep.guardrail` entries and cross-check `/metrics` for the histogram/counter series listed in §2.3; audit timestamps should appear <60 s from execution.
5. **Documentation Sync**
   - Update this section and the quickstart if prerequisites change; log revision in the Automation Appendix when sweeps trigger new waiver processes.
6. **Validation Scripts**
   - Run `poetry run pytest tests/perf/test_sweep_rejection_latency.py` prior to release to prove cap rejection latency remains <2 seconds.
   - Execute `poetry run pytest tests/governance/test_sweep_telemetry_latency.py` and `poetry run pytest tests/governance/test_sweep_data_quality_variance.py` to capture telemetry latency (<60 s) and SC-006 variance evidence.

Failing any prerequisite above requires remediation or recorded waiver before sweeps proceed.
- Tolerance Profile: <profile>
- Vendor Versions: <list>
- Dataset Hashes: <hashes>
- Baseline Version: <version>
- Waivers: <id + expiry or none>
- Tolerance Arbitration: <details or none>
- Cold Storage Copy: <path>
- Trust Gate Report Hash: <sha256>
- Logged By: <operator>
```

---

**References**
- Spec: `specs/011-trust-gate-framework/spec.md`
- Data Model: `specs/011-trust-gate-framework/data-model.md`
- Waiver Policy: `WAIVERS.md`
- Governance: `docs/governance/retention_policy.md`
