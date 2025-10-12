# Quickstart – Test Hardening & Coverage Elevation

## Prerequisites
- Python 3.11 with Poetry dependencies installed (`poetry install --with dev`).
- `psutil` dependency added to Poetry environment (install via `poetry add --group dev psutil` if not already present).
- Baseline artifacts present under `artifacts/` (determinism and perf baselines) or regenerated via existing scripts.
- Node.js 18+ with pnpm installed for regenerating the `alphaforge-mind` API client when the OpenAPI contract shifts (`pnpm install` inside `alphaforge-mind`).

## 1. Run Hardened Quality Gates Locally
```powershell
poetry run python scripts/ci/run_quality_gates.py
```
- Inspect `zz_artifacts/quality_gates_summary.json`; failing gates list under `failures`.
- To exercise failure fixtures manually, set the environment variable `AF_FORCE_QG_FAILURE=<gate>` for targeted debugging (implemented in Phase 1).

## 2. Execute Extended Test Suites
```powershell
poetry run pytest --cov=alphaforge-brain/src --cov-report=term-missing
```
- Coverage must remain ≥90% across line, branch, function, and integration layers; CI enforces this via `--cov-fail-under=90` and module-level assertions.
- Module-specific reports write to `zz_artifacts/coverage_policy.json`.

## 3. Validate Dataset Manifests
```powershell
poetry run python scripts/data/verify_manifests.py
```
- Generates or validates `dataset_manifest.json` files alongside canonical datasets.
- Any hash or schema drift aborts before tests proceed.

## 4. Run Memory Probe & Perf Gate
```powershell
poetry run python scripts/ci/memory_cap_probe.py --out zz_artifacts/memory_cap.json
poetry run python scripts/bench/perf_run.py --iterations 3 --warmup 1 --output zz_artifacts/perf_latest.json
poetry run python scripts/ci/run_perf_gates.py
poetry run pytest --no-cov tests/ci/test_perf_gates_script.py
```
- `memory_cap.json` records peak RSS vs configured limit; CI fails when `within_cap` is false.
- Perf run now emits a `perf_sla` record inside `zz_artifacts/perf_latest.json`, capturing `suite`, `mean_ms`, `p95_ms`, `baseline_mean_ms`, the enforced `limit_multiplier` (default **1.5×**), `pass`, `run_id`, and `generated_at` so governance tooling can parse the SLA verdict.
- Running `scripts/ci/run_perf_gates.py` produces `zz_artifacts/trust_gate_metrics.prom` (Prometheus snapshot) and hard-fails on SLA regressions with remediation guidance.
- Running the targeted CI wrapper test with `--no-cov` avoids tripping the global 90 % coverage floor when executing outside the primary test tree.

## 5. Review Governance Artifacts
- `zz_artifacts/quality_gates_summary.json`
- `zz_artifacts/coverage_policy.json`
- `zz_artifacts/memory_cap.json`
- `zz_artifacts/perf_latest.json`
- `zz_artifacts/trust_gate_metrics.prom`

Commit updated artifacts with care; baseline updates require waiver documentation in `docs/operations/trust_gates.md` and `WAIVERS.md`.

## 6. Sync Frontend API Contract
```powershell
poetry run python scripts/contracts/verify_frontend_contract.py --spec openapi.deref.json --out zz_artifacts/frontend_contract.json
Set-Location alphaforge-mind
pnpm install
pnpm run generate-client
pnpm run smoke:api
Set-Location ..
```
- `zz_artifacts/frontend_contract.json` records the diff status (`clean`, `needs_regen`, `blocked`).
- Regenerated TypeScript client artifacts must be committed in `alphaforge-mind` alongside any backend schema adjustments.
- Frontend smoke suite must pass before promoting the release; failures block the gate until resolved.
