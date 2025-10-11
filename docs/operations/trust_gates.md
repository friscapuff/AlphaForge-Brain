# Trust Gate Operations Guide

**Last Updated**: 2025-10-11
**Owner**: Release Steward (AlphaForge Brain)

This guide operationalizes the trust gate framework across ingest → transform → emit, ensuring compliance with constitutional principles and the newly introduced non-functional requirements.

## 1. Artifact Retention & Security Policy

| Artifact | Minimum Retention | Storage Requirements | Integrity Actions |
|----------|-------------------|----------------------|-------------------|
| `trust_gate_report.json` (signed) | 3 years | AES-256 encrypted disk or encrypted S3/GCS bucket | Quarterly re-hash rotation logged in §5 |
| `ingest_vendor_metadata.json`, retry traces | 18 months (540 days) | Same encryption standard as above | Monthly checksum verification |
| Waiver records referencing trust gates (`WAIVERS.md`, attachments) | Active + 90-day expiry window | Primary repo (git) + cold storage copy within 24 hours | Expiry audit during weekly governance review |
| Baseline & leak-catcher datasets | Per data governance policy (min 3 years) | Immutable artifact store (hash-addressed) | Regenerate with signed approval |

**Encryption Standard**
- Local storage: BitLocker or LUKS with AES-256.
- Cloud storage: S3/GCS buckets with default SSE-KMS or CMEK enforcing AES-256.
- Key rotation cadence: every 6 months (aligned with operations security playbook).

## 2. Performance Guardrails & Tolerance Profile

### 2.1 Runtime Limits (FR-211)

- **Benchmark harness**: `poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json`
   - The harness now emits `trust_gates.stages.trust_suite.total.mean_ms` and per-gate spans.
   - Raw iterations and stage breakdown live under the `trust_gates` key in the JSON payload (and the optional output file if `--output` is supplied).
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
5. Update `WAIVERS.md` if any new waivers issued; reconfirm expiries.

### Quarterly Maintenance
1. Execute hash rotation script:
   ```powershell
   poetry run python scripts/operations/rotate_trust_gate_hashes.py --since 90d
   ```
2. Address any mismatched hashes (investigate integrity breach, regenerate artifact if necessary).
3. Record the reported hash values in §6 (append manual note or run logging script in dry-run mode) with operator signature.

## 6. Automation Appendix (Attestations)

This section is auto-appended by the logging script.

```markdown
## Run Attestation: <RUN_ID>
- Executed: <timestamp UTC>
- Suite Version: <version>
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
