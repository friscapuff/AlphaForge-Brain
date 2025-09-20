# Project A Backend

<!-- Badges -->
![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.11.x-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-available%20in%20CI-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Benchmarks](https://img.shields.io/badge/bench-risk_slippage%20&%20perf_run-informational.svg)

Single-user deterministic backtesting & validation engine.

## Features
- FastAPI + Pydantic v2 backend
- Deterministic run hashing & idempotent submission
- SQLite (local) persistence (extensible to Postgres later)
- Structured logging (structlog + rich)
- Artifact manifest with SHA-256 integrity
- SSE event stream for run lifecycle
- Preset persistence (idempotent create by hash)
- Extensible feature engineering & indicator calculation pipeline
- Microbenchmark harness (performance profiling)

## Tech Stack
Python 3.11, FastAPI, Pydantic v2, SQLite, pandas/numpy, structlog, pytest, ruff, mypy, Poetry.

## Getting Started
### 1. Prerequisites
- Python 3.11.x
- Poetry >= 1.8

### 2. Install Dependencies
```powershell
poetry install --with dev
```
(Add extras as needed, e.g. `--extras "polars performance distributed"`)

### 3. Activate Shell
```powershell
poetry shell
```

### 4. Run App (Dev)
```powershell
poetry run uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### 4a. (Option C) Convenience Dev Script
Instead of remembering the uvicorn flags, use the helper script:
```powershell
pwsh scripts/dev/run_api.ps1 -Port 8000 -Reload -Workers 1
```
Parameters:
- `-Port` (default 8000)
- `-Reload` (enable code reload)
- `-Workers` (process count; omit with `-Reload` for single process reload reliability)
- `-BindHost` (default 0.0.0.0)

If you're already inside `poetry shell` it uses the active venv; otherwise it prefixes with `poetry run` automatically.

### 5. Run Tests
```powershell
poetry run pytest
```

### 6. Lint & Type Check
```powershell
poetry run ruff check .
poetry run mypy src
```

## Dependency Groups & Extras
- Dev group: pytest, hypothesis, coverage, ruff, mypy, pre-commit
- Extras:
  - polars: Polars dataframe engine
  - performance: numba acceleration
  - distributed: celery + redis + flower
  - storage: boto3 for S3-compatible artifact storage
  - integrity: hashlib-py (optional hashing variations)

Install with selected extras:
```powershell
poetry install --with dev --extras "polars performance"
```

## Data & Artifacts
Runs limited to last 100 (retention). Each run stores:
- Config (canonical JSON)
- Metrics summary
- Artifact manifest (filename, size, sha256)
- Optional feature matrices
- Validation summaries / detail (permutation, bootstrap, monte carlo, walk-forward)

## Presets
Reusable parameter sets for interactive UI workflows. Create:
```powershell
curl -X POST http://localhost:8000/presets -H "Content-Type: application/json" -d '{
  "name": "dual_sma_default",
  "config": {
    "symbol": "TEST",
    "timeframe": "1m",
    "start": "2024-01-01",
    "end": "2024-01-02",
    "indicators": [{"name": "dual_sma", "params": {"fast": 5, "slow": 20}}],
    "strategy": {"name": "dual_sma", "params": {}},
    "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
    "execution": {"slippage_bps": 5, "fee_bps": 0},
    "validation": {},
    "seed": 42
  }
}'
```
List:
```powershell
curl http://localhost:8000/presets
```
Get:
```powershell
curl http://localhost:8000/presets/<preset_id>
```
Delete:
```powershell
curl -X DELETE http://localhost:8000/presets/<preset_id>
```
Re-posting identical payload returns the same `preset_id` (idempotent).

## Microbenchmarks

End-to-end orchestration latency:
```powershell
poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1
```
Sample output (abridged):
```json
{
  "runs": {
    "iterations": 5,
    "mean_sec": 0.18,
    "median_sec": 0.17,
    "p95_sec": 0.20
  }
}
```
Risk & slippage model micro timings:
```powershell
poetry run python scripts/bench/risk_slippage.py --iterations 300 --risk-models fixed_fraction,volatility_target,kelly_fraction --slippage none,spread_pct,participation_rate
```
Outputs JSON keyed by `risk:<model>` and `slippage:<model>` with microsecond stats.

Makefile shortcuts:
```powershell
make bench
```

## OpenAPI & Contracts
See `specs/001-initial-dual-tier/contracts/openapi.yaml` for REST & SSE schema.

## Project Layout
```
src/
  api/            # FastAPI app, routers, error handlers
  domain/         # Core domain logic (entities, services)
  infra/          # DB, config, logging, utils, migrations
specs/            # Design + research artifacts
```

## Common Tasks
```powershell
# Add a new dependency
poetry add some-package

# Add a dev-only dependency
poetry add --group dev pytest-xdist

# Add an optional extra dep (edit pyproject then lock)
poetry lock

# Update all
poetry update
```

## Reproducibility
`poetry.lock` ensures exact versions. Commit it. Hashes ensure run determinism; changing config or code producing features will alter the run hash.

### Reproducibility Addendum (Deterministic Reruns)
Each run hash = SHA-256 of a canonical JSON serialization of the submitted `RunConfig` (plus fixed ordering). To precisely reproduce a past run:

1. Capture original POST body (the exact JSON you sent to `/runs`).
2. Ensure identical code + dependency set (sync your branch & `poetry install --no-root` using the same `poetry.lock`).
3. Ensure the `seed` field is present (if omitted originally, the orchestrator default may differ across versions; always include it for strict reproducibility).
4. POST the identical JSON again. If the hash matches an existing run you'll get a 200 with the same `run_hash` (idempotent reuse) and artifacts will not be recomputed.
5. Fetch artifacts and events identically (e.g. `/runs/{run_hash}/artifacts`, `/runs/{run_hash}/events`).

Sample minimal payload (dual SMA):
```json
{
  "symbol": "TEST",
  "timeframe": "1m",
  "start": "2024-01-01",
  "end": "2024-01-02",
  "indicators": [
    {"name": "sma", "params": {"window": 5}},
    {"name": "sma", "params": {"window": 15}}
  ],
  "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
  "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
  "execution": {"slippage_bps": 0, "fee_bps": 0, "borrow_cost_bps": 0},
  "validation": {"permutation": {"trials": 3}},
  "seed": 42
}
```

Quick verification loop (PowerShell):
```powershell
$payload = '{
  "symbol": "TEST", "timeframe": "1m", "start": "2024-01-01", "end": "2024-01-02",
  "indicators": [ {"name": "sma", "params": {"window": 5}}, {"name": "sma", "params": {"window": 15}} ],
  "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
  "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
  "execution": {"slippage_bps": 0, "fee_bps": 0, "borrow_cost_bps": 0},
  "validation": {"permutation": {"trials": 3}},
  "seed": 42
}'
1..2 | ForEach-Object {
  $resp = curl -Method POST -Uri http://localhost:8000/runs -H @{"Content-Type"="application/json"} -Body $payload
  $json = $resp.Content | ConvertFrom-Json
  Write-Host "Attempt $_ -> run_hash: $($json.run_hash)"
}
```
Both attempts should display the same `run_hash`.

Artifacts integrity: `manifest.json` includes `manifest_hash` (hash of manifest contents) and `chain_prev` linking to the previous run's manifest hash (linear chain for provenance).

## Docker & Virtualization Troubleshooting
If Docker Desktop reports "Virtualization support not detected" or engine stopped:

1. Run the diagnostic script:
```powershell
pwsh scripts/env/check_virtualization.ps1 -Json virt_report.json
```
2. Open `virt_report.json` and look at `evaluation.overall_ready`.
3. Remediation mapping:
  - `firmware_virtualization = FAIL` → Enable VT-x / SVM in BIOS/UEFI.
  - `wsl2_distro_present = NO` → `wsl --install -d Ubuntu` (then reboot) or convert existing: `wsl --set-version <Name> 2`.
  - `feature_status.VirtualMachinePlatform != Enabled` → Enable Windows feature (see script hints).
  - `bcd_hypervisorlaunchtype = NOT_AUTO` → `bcdedit /set hypervisorlaunchtype auto` then reboot.

You can develop without Docker (use the dev run script) until ready.

## Next Steps
- Refine OpenAPI examples for advanced validation configs
- Add container packaging & optional production tuning docs

---
Generated initially via automated architecture scaffolding. Iterate with discipline: test-first, small commits, contract fidelity.
