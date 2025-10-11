# Validation Evidence: Trust Gate Framework

**Feature**: 011-trust-gate-framework
**Prepared**: 2025-10-11
**Owner**: Trust Gate Governance WG

## 1. Summary Table

| Evidence Type | Command / Source | Artifact(s) | Result | Timestamp |
|---------------|------------------|-------------|--------|-----------|
| Runtime guard perf test | `poetry run pytest alphaforge-brain/tests/perf/test_trust_gate_runtime.py -q` | `zz_artifacts/perf_latest.json`, `artifacts/perf_baseline.json` | PASS — mean 0.0 ms ≤ 42.73 ms limit | 2025-10-11 |
| Benchmark harness capture | `poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json` | `zz_artifacts/perf_latest.json` | PASS — trust_suite.total.mean_ms 0.0 | 2025-10-11T11:36:44Z |
| Mind dashboard / metrics parser test | `npm test -- --run tests/unit/observability/trustGateMetrics.test.ts` | `alphaforge-mind/tests/unit/observability/trustGateMetrics.test.ts` | PASS — 2 tests | 2025-10-11T14:40:18Z |

## 2. Artifacts

- `zz_artifacts/perf_latest.json` — Latest benchmark payload including `trust_suite.total.mean_ms` and per-gate spans. Stored in repo root for audit attachment.
- `artifacts/perf_baseline.json` — Masters baseline reference (28.49 ms mean). Verified during runtime guard test.
- `artifacts/trust_gates/reports/*` — Signed trust gate reports (see security memo for retention requirements).

## 3. Log References

- Pytest output appended to release PR comment (see CI run `trust-gate-runtime`).
- Benchmark harness log stored at `zz_artifacts/perf_latest.log` when run with `--verbose` (optional; not present by default).
- Vitest output recorded in local run (see section 4 for reproduction steps).

## 4. Reproduction Steps

1. Ensure Python virtualenv active (`poetry shell`) and Node dependencies installed (`npm install` under `alphaforge-mind`).
2. Run benchmark harness and runtime guard test:
   - `poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json`
   - `poetry run pytest alphaforge-brain/tests/perf/test_trust_gate_runtime.py -q`
3. From `alphaforge-mind/`, execute `npm test -- --run tests/unit/observability/trustGateMetrics.test.ts` to validate metrics parser.
4. Attach resulting artifacts/log snippets to release checklist.

## 5. Requirement Coverage

### Functional Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-201 Trust gate harness CLI and signed report | ✅ | `poetry run trust-gates` flow documented in `quickstart.md`; signed artifacts emitted by `alphaforge-brain/src/services/trust_gates/report_writer.py`; CLI contract captured in `contracts/cli-trust_gates.example.txt`. |
| FR-202 Golden-run determinism comparison | ✅ | Gate implementation in `alphaforge-brain/src/services/trust_gates/gates/golden_run.py`; integration test `tests/integration/trust_gates/test_golden_run_gate.py`; reports attached in `artifacts/trust_gates/reports/*`. |
| FR-203 Causality (leak-catcher) audit | ✅ | Gate implementation `gates/causality.py`; dataset metadata in `presets/leak_catcher`; test `tests/integration/trust_gates/test_causality_gate.py`; metrics surfaced in trust gate report. |
| FR-204 Equity reconciliation | ✅ | Gate implementation `gates/equity.py`; test `tests/integration/trust_gates/test_equity_and_accounting_gates.py`; metrics recorded in trust gate report. |
| FR-205 Universe stamp verification | ✅ | Gate implementation `gates/universe.py`; test `tests/integration/trust_gates/test_universe_stamp_gate.py`; governance tolerances in `configs/trust_gates/tolerances/institutional_default.yaml`. |
| FR-206 Ingest idempotency | ✅ | Gate implementation `gates/ingest.py`; integration test `tests/integration/trust_gates/test_ingest_idempotency_gate.py`; vendor metadata persisted and referenced in security memo. |
| FR-207 Timezone normalization | ✅ | Gate implementation `gates/timezone.py`; test `tests/integration/trust_gates/test_timezone_gate.py`; metrics logged in trust gate report. |
| FR-208 Accounting reconciliation | ✅ | Gate implementation `gates/accounting.py`; test `tests/integration/trust_gates/test_equity_and_accounting_gates.py`; tolerance profile documented. |
| FR-209 Persistence & API surfaces | ✅ | Alembic migration + manifest writers (T040–T047); contracts in `contracts/api-run.trust_gate.example.json`; manifest example and Mind adapter (`alphaforge-mind/src/services/api/backtests.ts`). |
| FR-210 CI & governance integration | ✅ | Pipeline script `scripts/ci/run_trust_gates.ps1`; governance updates in `WAIVERS.md` and `docs/governance/retention_policy.md`; decision record §5. |
| FR-211 Observability & Prometheus metrics | ✅ | Telemetry module `alphaforge-brain/src/services/trust_gates/telemetry.py`; benchmark harness augmentation (T050); Mind dashboard + toast consuming metrics (`TrustGatePanel`, `TrustGateAlertToast`) with tests. |
| FR-212 Documentation currency | ✅ | Updated `docs/operations/trust_gates.md`, quickstart, README, security memo; validation evidence maintained in this file. |
| FR-213 Selective execution for local debugging | ✅ | CLI `--only` implementation (T030/T031) with documentation in quickstart and contract tests `tests/cli/test_trust_gates_entrypoint.py`. |

### Non-Functional Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| NFR-201 Vendor metadata retention & encryption | ✅ | `docs/security/trust_gate_metadata.md` §2–4; retention policy cross-reference and Key Vault usage. |
| NFR-202 Signed report retention (3 years) | ✅ | Security memo §4; retention policy §7; artifact storage workflow describes lifecycle rules. |
| NFR-203 Waiver expiry & cold storage | ✅ | `WAIVERS.md` guidance plus governance policy updates; CI gating enforces waiver presence. |
| NFR-204 Solo steward lineage logging | ✅ | `docs/operations/trust_gates.md` updated with runbook notes; governance decision record callouts. |

All evidence recorded; attach referenced artifacts to the release checklist during sign-off.
