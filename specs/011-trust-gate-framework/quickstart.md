# Quickstart: Trust Gate Framework

Feature: 011-trust-gate-framework
Related Documents: [spec](./spec.md) · [plan](./plan.md) · [research](./research.md) · [data model](./data-model.md)

## Overview
This quickstart walks through running the trust gate suite locally, interpreting results, and regenerating baselines. The suite enforces determinism, causality, ingest integrity, timezone alignment, universe completeness, equity reconciliation, and accounting balance before a run can proceed to Masters validation.

## Prerequisites
- Python 3.11 environment with project dependencies installed (`poetry install`).
- Access to baseline artifacts under `artifacts/trust_gates/baselines/`.
- Credentials/configuration for ingest vendors (if idempotency gate runs against live APIs).
- Signing key available for trust gate report signature (configured via `AF_TRUST_GATES_SIGNING_KEY`).

## Running the Trust Gate Suite
```powershell
# Activate env (if not already active)
poetry shell

# Execute full suite with default tolerances
poetry run trust-gates

# Run a subset for debugging (not allowed in CI)
poetry run trust-gates --only causality,accounting
```

### Expected Output
Refer to `contracts/cli-trust_gates.example.txt` for sample output. The command exits with non-zero status if any gate fails or if baseline artifacts are missing and no waiver is present.

## Artifacts & Reports
| Artifact | Location | Description |
|----------|----------|-------------|
| `trust_gate_report.json` | `artifacts/trust_gates/reports/{run_id}/` | Signed summary of gate outcomes, metrics, tolerances, and correlation IDs. |
| `gate_{name}_diagnostics.json` | `artifacts/trust_gates/reports/{run_id}/` | Gate-specific diagnostics (hash diffs, leakage scores, missing symbols, etc.). |
| `ingest_vendor_metadata.json` | Same directory | Vendor version info, retry events, API rate limits. |
| `trust_gate_report.sig` | Same directory | Detached signature for the suite report. |

## Baseline Management
```powershell
# Regenerate golden-run baseline (requires governance approval)
poetry run trust-gates --refresh-baseline --baseline-version v3
```
- The command writes new baseline artifacts under `artifacts/trust_gates/baselines/{version}` and records signer metadata.
- Update `AF_TRUST_GATES_BASELINE_VERSION` or config file to point to the new baseline.

## Performance Guardrails
- **Benchmark harness**: `poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json`
  - The JSON output includes a `trust_gates` section with `stages.trust_suite.total.mean_ms` and per-gate spans.
- **Runtime limit**: `trust_suite.total.mean_ms` must stay at or below **1.5×** the Masters baseline mean stored in `artifacts/perf_baseline.json` (currently 28.49 ms → limit 42.73 ms).
- **Automation**: `pytest alphaforge-brain/tests/perf/test_trust_gate_runtime.py -m perf` enforces the guard; update baselines or file a waiver if the limit is exceeded.
- **Gate tolerances**: Institutional defaults require zero hash drift, UTC timestamps, ≤5 bps equity/accounting divergence, and leakage ≤0.05. See `docs/operations/trust_gates.md` §2 for the full table and waiver process.

## Failure Triage
1. Inspect CLI output or `trust_gate_report.json` to identify failing gate(s).
2. Review corresponding diagnostics artifact for details.
3. If failure results from intentional change, file waiver entry in `WAIVERS.md` referencing FR and remediation plan.
4. If failure indicates data drift (e.g., missing symbols), coordinate with Data Governance to restore dataset and rerun.

## Observability & Metrics
- Structured logs emit `trust_gate` events with status, duration, and tolerance information.
- Prometheus metrics exposed via `/metrics`:
  - `trust_gate_status{gate="golden_run"} = 1` on success, `0` on failure.
  - `trust_gate_duration_seconds{gate}` histogram capturing runtime.
  - `trust_gate_failures_total{gate}` counter for alerting when repeated failures occur.

## Next Steps
- Integrate trust gate summary into Mind dashboards (consume API contract in `contracts/api-run.trust_gate.example.json`).
- Extend CI pipeline to run trust gates before Masters validation stage and enforce merge blocking on failure.
- Document governance workflow for baseline regeneration and waiver issuance in `docs/operations/trust_gates.md`.
