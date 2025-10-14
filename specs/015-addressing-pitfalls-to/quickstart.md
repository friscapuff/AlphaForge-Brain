# Quickstart: Operational Guardrail Remediation

## Prerequisites
- Python 3.11 environment managed by Poetry
- Access to Prometheus/Alertmanager stack used by AlphaForge Brain
- Existing benchmark baseline at `artifacts/perf_baseline.json`
- Permissions to update `WAIVERS.md`, `docs/operations/` runbooks, and CI configuration

## Step 1: Profiling Sprint & Benchmark Harness
1. Install development dependencies:
   ```powershell
   poetry install --with dev
   ```
2. Regenerate benchmark payload that feeds profiling (full run recommended for evidence; use `--iterations 1 --warmup 0` for a quick smoke):
   ```powershell
   poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json
   ```
3. Build the validation performance report from the latest payload (set `--input` if you saved the payload elsewhere; override `--output` to capture under `zz_artifacts/profiling/latest.json`):
   ```powershell
   poetry run python scripts/bench/profiling/run_validation_profiling.py --input zz_artifacts/perf_latest.json --output zz_artifacts/profiling/latest.json
   ```
4. Verify runtime guardrail and capture alert status:
   ```powershell
   poetry run python scripts/bench/compare_baseline.py --baseline artifacts/perf_baseline.json --latest zz_artifacts/perf_latest.json
   ```
   Ensure delta ≤ 10%.

## Step 2: Configure CI Schema Validation
1. Update JSON Schema files under `configs/schemas/` for tolerance and retention YAML.
2. Implement validation script:
   ```powershell
   poetry run python scripts/ci/validate_configs.py
   ```
3. Add GitHub Actions step before test jobs to execute the script and check for signed change logs.

## Step 3: Observability & Alerts
1. Extend parquet doctor instrumentation (set `PYTHONPATH` so package-relative imports resolve):
   ```powershell
   set PYTHONPATH=alphaforge-brain\src; poetry run python -m infra.cache.doctor --root cache/candles
   ```
2. Confirm Prometheus scrapable metrics are present and Alertmanager rule `ParquetFallbackHigh` is active.
3. Trigger test fallback alert (simulate or use staging) and verify paging notification within 5 minutes.

## Step 4: Waiver Cadence Automation
1. Generate cadence snapshot:
   ```powershell
   poetry run python scripts/ci/waiver_cadence.py --waivers WAIVERS.md --out zz_artifacts/governance/waiver_cadence.json
   ```
2. Confirm dashboard ingestion of the JSON artifact.
3. Validate escalation emails/alerts fire for waivers ≥45 days when script runs in CI.

## Step 5: Sweep Acceptance Suite
1. Execute deterministic acceptance tests:
   ```powershell
   poetry run pytest alphaforge-brain/tests/sweeps/test_acceptance.py
   ```
2. Inspect generated manifests in `alphaforge-brain/tests/data/sweeps/expected/` and ensure runbook links are valid.

## Step 6: Documentation & Runbook Update
1. Update `docs/operations/trust_gates.md` and `docs/operations/validation_backfill.md` with mitigation references.
2. Add new runbook section mapping each mitigation to FR/SC IDs.
3. Attach outputs (profiling report in `zz_artifacts/profiling/latest.json`, alert screenshots, cadence summary in `zz_artifacts/governance/waiver_cadence.json`) to the governance evidence directory.

## Verification Checklist
- [ ] Validation runtime ≤ 110% baseline for last 30 days
- [ ] Benchmark alert fired during test and created tracking ticket
- [ ] CI blocks malformed tolerance/retention change
- [ ] Parquet fallback alert pages on-call in staging test
- [ ] Waiver cadence report shows no items >60 days
- [ ] Sweep acceptance suite passes with deterministic ordering documented
- [ ] Runbook updated with FR/SC mapping
