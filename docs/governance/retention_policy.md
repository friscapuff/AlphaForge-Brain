# Masters Validation Retention & Promotion Policy

> Updated: 2025-10-10 · Owners: Validation WG (Brain Platform), Data Governance, Compliance Liaison

## 1. Purpose & Scope
This policy governs how AlphaForge promotes, retains, or demotes backtest runs after the Masters validation rollout (Feature 010). It complements the existing retention engine (`alphaforge-brain/src/services/retention/policies.py`) and documents the governance gates that now depend on Masters modules (permutation, Sharpe deflation, cross-validation, execution realism). Historical guidance is preserved in the repository history; this document supersedes prior informal notes.

## 2. Effective Date
- **Activation**: Immediately for all runs executed after migration `20251010001_validation_schema_v2`.
- **Historical runs**: Default to neutral/waived status until processed through the [Masters Validation Backfill Playbook](../operations/validation_backfill.md).

## 3. Validation Gates & Outcomes
| Gate | Criteria | Auto-Promotion? | Required Action | Notes |
|------|---------|-----------------|-----------------|-------|
| **Permutation Significance** | `validation_significance` = `fail` (p-value > configured threshold, default 0.01) | **Block** | Rerun strategy, adjust configuration, or submit waiver reviewed by Validation WG + Governance | Threshold derived from Masters methodology; see [`validation_schema_v2`](../decisions/validation_schema_v2.md). |
| **Permutation Caution** | `validation_significance` = `caution` | Conditional | Data reviewer must document mitigation (e.g., lower confidence capital allocation) before promotion | Promotion allowed only with written acknowledgement; leverage `WAIVERS.md` template if overriding. |
| **Sharpe Bias Adjustments** | DSR or PSR flagged `fail` or `bias_flag=true` | **Block** | Investigate parameter search breadth / multiple testing; provide remediation plan | Bias flag triggers when CSCV-adjusted Sharpe breaches 0.25 absolute or 20% relative drop. |
| **Cross-Validation Leakage** | `leakage_score` > `AF_LEAKAGE_THRESHOLD` (default 0.1) | **Block** | Confirm purge span; if legitimate data dependency, document and freeze config | Default purge span = max(30 days, strategy lookback). |
| **Execution Realism** | `status = fail` (cost/impact/capacity over budget) | **Block** | Adjust trade sizing, execution pacing, or cost assumptions; attach evidence to waiver if overriding | Budgets sourced from `AF_REALISM_CAPACITY_BPS_LIMIT` and strategy cost flags. |
| **Runtime SLA** | `validation.total` mean exceeds guardrail (`34 ms` baseline × 1.2) | **Monitor** | No promotion block, but backlog runs must note SLA breach in release checklist | Current benchmark: ~1543 ms total (10-11-2025); remediation work tracked separately.

Auto-promotion flows (e.g., CI “promote latest run”) must validate these gates before marking a run as `full`. Failed gates downgrade the run to `manifest-only` until remediated or waived. Implementation lives in `alphaforge-brain/src/services/retention/policies.py`.

## 4. Review & Sign-Off Workflow
1. **Validation WG** confirms the run artifacts contain Masters payloads (permutation parquet files, bias metrics, CPCV fold manifest, realism summary). Until aggregator wiring lands, reviewers may reference `validation_detail.json` for full metrics (see Phase 3.5 note).
2. **Data Governance** verifies purge span and leakage assumptions align with [`validation_schema_v2`](../decisions/validation_schema_v2.md).
3. **Compliance Liaison** ensures execution realism warnings and recommended remediation are documented before capital deployment.
4. Sign-offs are recorded in the release checklist or a dedicated entry within `WAIVERS.md` when overrides occur.

## 5. Waiver Procedure
- Waivers follow the template in `WAIVERS.md`. Provide:
  - Run hash and artifact paths.
  - Failed gate(s) with metrics (e.g., permutation p-value, leakage score).
  - Business justification and temporary mitigation.
  - Expiry date for waiver review.
- Required approvers: Validation WG lead, Data Governance representative, and Compliance Liaison.

## 6. Historical Backfill Expectations
- Teams must schedule replay of legacy “golden” runs using the [Masters Validation Backfill Playbook](../operations/validation_backfill.md) prior to quarterly audits.
- Backfilled runs inherit the gate outcomes above; if a replay fails due to SLA gaps, record the incident and scale permutation counts temporarily (documented in the playbook).

## 7. Monitoring & Reporting
- Benchmarks: Maintain the latest validation runtime snapshot at `zz_artifacts/validation_smoke.json`; include it in quarterly governance packets until SLA regression resolved.
- Telemetry: Structlog `validation_span` events feed the ops dashboard; Governance reviews outliers weekly.
- Audit Trail: Manifest metadata must record `validation_schema_version = 2` and module statuses. Pending aggregator work (Phase 3.5) renders placeholder values; track completion in T027/T030 follow-ups.

## 8. Change Log
| Date | Change | Authors |
|------|--------|---------|
| 2025-10-10 | Initial Masters governance update (T047). Added gating table, waiver workflow, SLA context, and cross-references to decision record & backfill playbook. | Validation WG |

## 9. Related References
- [`docs/decisions/validation_schema_v2.md`](../decisions/validation_schema_v2.md)
- [`docs/operations/validation_backfill.md`](../operations/validation_backfill.md)
- `alphaforge-brain/src/services/retention/policies.py`
- `alphaforge-brain/src/services/validation/aggregator.py`
