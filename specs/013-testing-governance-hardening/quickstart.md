# Quickstart: Testing Governance Hardening

## Prerequisites
- Poetry environment installed (`poetry install` already provisioned).
- Access to `alphaforge-brain` repository with updated `configs/` files.
- Prometheus endpoint configured to scrape trust-gate metrics.

## 1. Configure Tolerances & Retention
1. Copy the sample SLA to a working profile:
   ```powershell
   Copy-Item configs\trust_gates\tolerances\institutional_default.yaml configs\trust_gates\tolerances\causality.yaml
   ```
2. Edit thresholds and bump `schema_version` as needed.
3. Review `configs/retention/policy.yaml` and set defaults for `max_runs` and `per_strategy_top`.

## 2. Run Validation Gates
```powershell
poetry run python -m alphaforge_brain.services.trust_gates.suite_service --run-hash <hash>
```
- Expect runs violating tolerances to exit with `FAILED_VALIDATION`.
- Prometheus counter `trust_gate_failure{gate="causality"}` increments on failure.

## 3. Apply Retention Sweep
```powershell
poetry run python -m alphaforge_brain.services.retention.sweeper
```
- Pinned runs exceeding policy remain; breach logged to `zz_artifacts/retention_breaches.log`.
- Use CLI to manage pins:
  ```powershell
  poetry run alphaforge-brain retention pin --run-hash <hash>
  poetry run alphaforge-brain retention unpin --run-hash <hash>
  poetry run alphaforge-brain retention policy inspect
  ```

## 4. Verify Persistence Schemas
```powershell
poetry run python scripts/migrations/validate_persistence.py --schema-version <version>
```
- Ensures payloads include `schema_version` and validate against JSON Schema contracts.

## 5. Test Runtime Import Guard
```powershell
poetry run python scripts/dev/test_cross_root_guard.py
```
- Should raise `CrossRootImportError` when attempting `import alphaforge_mind` from Brain runtime.
- Blocked attempts are logged to `zz_artifacts/import_guard/events.json`; include the latest entry when filing governance reports.

## 6. Execute Test Suite
```powershell
poetry run pytest --cov=alphaforge_brain --cov-report=xml \
  tests/services/trust_gates \
  tests/services/retention \
  tests/services/validation
poetry run ruff check alphaforge-brain/src tests
poetry run mypy --config-file mypy.strictplus.ini alphaforge-brain/src
```
- Coverage XML lands at `coverage.xml`; copy or rename to `zz_artifacts/coverage/governance/phase_<n>.xml` (matching the active phase) for sign-off.
- Optional: run `poetry run pytest tests/api/routes/test_runs_promotion_failed_validation.py` for targeted API gating verification before promotion.

## 7. Promote Run via API
```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://api.alphaforge.internal/runs/<hash>/promotion" `
  -ContentType "application/json" `
  -Body (@{ waiver_id = "<waiver-or-null>" } | ConvertTo-Json)
```
- Expect HTTP `409` unless a valid waiver accompanies a `FAILED_VALIDATION` run.

## Troubleshooting
- Missing tolerance config → gate exits with `FAILED_VALIDATION` and `trust_gate_config_error` metric.
- Schema mismatch → persistence insert rejected; inspect logs under `zz_artifacts/schema_errors.log`.
- Retention breach logs require follow-up waiver entry in `WAIVERS.md`.
