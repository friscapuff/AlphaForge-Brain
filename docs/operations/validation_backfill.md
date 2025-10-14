# Masters Validation Backfill Playbook

> Maintainers: Validation & Data Services · Last updated: 2025-10-10

## Purpose
This playbook documents how to enrich historical AlphaForge runs with Masters validation artifacts after deploying schema v2 (see `docs/decisions/validation_schema_v2.md`). It fulfils FR-016 by outlining a safe, repeatable process to:

- Detect runs created before the Masters rollout (no schema v2 metadata).
- Re-run those configurations with the new validation pipeline.
- Persist the upgraded artifacts, manifests, and runtime metrics without breaking determinism.

## When to Use
- After promoting the Masters validation release to staging or production.
- When historical “golden” backtests require statistical evidence before audit reviews.
- Prior to decommissioning legacy validation outputs (block-bootstrap, MC-only).

If neutral defaults are sufficient for a backlog, you may skip this playbook; all new runs already emit schema v2 payloads automatically.

## Prerequisites
1. **Environment**: Poetry virtualenv activated (`poetry install` already completed). Node is not required.
2. **Database**: `studio.db` located at the repository root (default). Back up the file before any mutation:
   ```powershell
   copy studio.db studio.db.before_validation_backfill
   ```
3. **Migrations**: Validate that revision `20251010001_validation_schema_v2` (or later) has been applied. Run the lightweight python runner:
   ```powershell
   poetry run python - <<'PY'
   from alphaforge_brain.infra.db import get_connection
   from alphaforge_brain.infra.alembic.runner import apply_python_migrations

   with get_connection() as conn:
       apply_python_migrations(conn)
   PY
   ```
   If this finishes silently, migrations are current.
4. **Validation Toggles**: Export Masters modules so the reruns capture full payloads (PowerShell shown):
   ```powershell
   $env:AF_VALIDATION_MODULES="permutation,dsr,psr,purged_kfold,cpcv,realism"
   $env:AF_VALIDATION_PERMUTATION_COUNT="500"
   $env:AF_VALIDATION_SIGNIFICANCE_THRESHOLD="0.01"
   $env:AF_LEAKAGE_THRESHOLD="0.1"
   $env:AF_REALISM_CAPACITY_BPS_LIMIT="500"
   ```
   Use `export` instead of `$env:` on Unix shells.

## Step 1 — Identify Runs that Need Backfill
Run the following SQL against `studio.db` (can be executed via the sqlite CLI or Python) to list candidates:
```sql
SELECT run_hash,
       datetime(created_at, 'unixepoch') AS created_at_utc,
       validation_schema_version,
       status
FROM runs
WHERE validation_schema_version IS NULL
   OR validation_schema_version < 2
ORDER BY created_at DESC;
```
Optional filters:
- Restrict to completed runs: `AND status = 'completed'`
- Limit to specific strategies: inspect `config_json` for the `strategy.name` key.

Export the resulting `run_hash` values; these will be reprocessed in Step 3.

## Step 2 — Stage Artifact Storage
Ensure you have space under `artifacts/` because each rerun will generate validation parquet files and updated manifests. If you need a dry run first, set `--keep-artifacts` to `False` in Step 3 to confirm runtime without persisting output.

## Step 3 — Rehydrate and Replay Configurations
Use the embedded Python helper below to iterate over the pending runs. It reads the original configuration JSON, submits it through `create_or_get`, and keeps the original hash (deterministic).

```powershell
poetry run python - <<'PY'
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "alphaforge-brain" / "src"
if str(SRC) not in sys.path:
   sys.path.insert(0, str(SRC))

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import RunConfig
from infra.db import get_connection


def pending(conn):
   query = """
   SELECT run_hash, config_json
   FROM runs
   WHERE (validation_schema_version IS NULL OR validation_schema_version < 2)
     AND status = 'completed'
   ORDER BY created_at
   """
   for row in conn.execute(query):
      yield row[0], json.loads(row[1])


with get_connection() as conn:
   registry = InMemoryRunRegistry()
   for run_hash, cfg_json in pending(conn):
      cfg = RunConfig.model_validate(cfg_json)
      new_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
      if new_hash != run_hash:
         raise RuntimeError(f"Hash drift detected: {run_hash} -> {new_hash}")
      print(
         f"[backfill] {run_hash} created={created} "
         f"validation_schema={record.get('validation_schema_version')}"
      )
PY
```

Key notes:
- `create_or_get` reuses cached results when available. The first replay may take minutes per run because permutation trials dominate runtime (current baseline ≈1543 ms validation span vs 34 ms SLA limit; see `docs/decisions/validation_schema_v2.md`).
- The helper intentionally raises on hash drift to protect determinism. Investigate any mismatch before proceeding.
- If you have dozens of runs, split them into batches by augmenting the SQL query with `LIMIT/OFFSET` or filtering on `created_at`.

### Alternative: API-Based Replay
If you prefer to send jobs through the running API service (preserving external observability), use `scripts/verify_replay.py` as a template—supply the original run configuration payload and ensure the API process points at the same `studio.db` and artifact root.

## Step 4 — Validate Outputs
After the reruns complete:

1. **Database sanity**
   ```sql
   SELECT COUNT(*)
   FROM runs
   WHERE validation_schema_version < 2;
   ```
   Expect `0` for a fully backfilled environment. If some rows remain, inspect their status (`status != 'completed'` or intentionally skipped).

2. **Artifact inspection**
   For each rerun hash, confirm the presence of Masters artifacts:
   - `artifacts/<RUN_HASH>/validation/permutation/segment_in_sample.parquet`
   - `artifacts/<RUN_HASH>/validation/permutation/segment_walk_forward.parquet`
   - `artifacts/<RUN_HASH>/validation_detail.json`

3. **CLI summary**
   ```powershell
   poetry run python alphaforge-brain/scripts/validation/show_summary.py --run-id <RUN_HASH>
   ```
   As soon as the manifest writer patch lands, the CLI will report schema version `2` and enumerate Masters metrics. During Phase 3.5 you may still see placeholders (`unknown` schema, empty module lists); rely on `validation_detail.json` in that interim.

4. **SLA snapshot**
   Run the single-iteration benchmark to record updated timings:
   ```powershell
   poetry run python scripts/bench/perf_run.py --iterations 1 --warmup 0 --keep-artifacts --output zz_artifacts/validation_smoke.json
   ```
   Archive the JSON with your runbook notes; it now represents a post-backfill benchmark.

## Sweep Acceptance Evidence (FR-006 / SC-006)

Run the deterministic sweep acceptance suite once Masters validation backfill completes. The suite ensures the mitigation catalogue remains auditable and that sweep behaviour complies with FR-006 (multi-ticker acceptance coverage) and SC-006 (evidence published within one business day).

```powershell
poetry run pytest alphaforge-brain/tests/sweeps/test_acceptance.py
poetry run python - <<'PY'
from services.orchestration import sweep_acceptance

sweep_acceptance.run_acceptance_suite()
PY
```

The second command writes `zz_artifacts/governance/sweep_acceptance.json`, a signed-off ledger of `SweepAcceptanceResult` entries. Attach the JSON (or its hash) to the weekly governance packet.

### Partial Cap Remediation

Scenario **`partial-cap-limit-enforced`** demonstrates that combination caps reject excess permutations while preserving deterministic ordering. The acceptance suite verifies:

- `cap_status` resolves to `hit` when the observed manifest records a cap breach.
- Associated anomaly flag `partial_execution` is routed to the governance dashboard.
- Runbook reference: https://github.com/alphaforge/docs/operations/validation_backfill.md#partial-cap-remediation (this section) must be cited in post-mortems.
- Compliance notes: satisfies FR-006 evidence requirement for partial-cap guardrails.

### Deterministic Ordering

Scenario **`deterministic-baseline-validation`** provides the control sample for expected vs observed ordering. Operators should reconfirm that no anomaly flags are emitted and that ordering arrays stay byte-for-byte identical. Any drift requires a baseline refresh or regression analysis before sweeps continue.

The anomaly scenario (**`anomaly-ordering-drift`**) is documented in the trust gate guide (§Sweep Anomaly Investigation) and links back into this playbook through the governance evidence bundle produced above.
Compliance notes: satisfies SC-006 deterministic ordering requirement for the baseline scenario.

## Rollback Plan
- Restore the `studio.db` backup taken in prerequisites.
- Remove any newly created `artifacts/<RUN_HASH>` directories if they conflict with older copies.
- Unset validation env vars if they were temporarily enabled: `Remove-Item Env:AF_VALIDATION_MODULES` (PowerShell) or `unset AF_VALIDATION_MODULES` (bash).

## Troubleshooting
| Symptom | Likely Cause | Remediation |
|---------|--------------|-------------|
| `hash drift detected` error | Config JSON mutated since original run (e.g., manual edit) | Stop, restore backup, compare `config_json` against historical manifest before re-running. |
| `validation_schema_version` remains `NULL` | Run crashed mid-way (permutation SLA breach) | Re-run with smaller permutation count (`AF_VALIDATION_PERMUTATION_COUNT=128`) to confirm pipeline, then scale back up. |
| CLI summary prints placeholders only | Manifest writer update not deployed yet | Use `validation_detail.json` for module metrics; doc revisions will cover the final manifest wiring (tracked by T027 follow-up). |
| SQLite locked errors | Concurrent processes writing to `studio.db` | Retry after stopping background API jobs or copy the database for offline replays.

## Appendices
- **Decision record**: `docs/decisions/validation_schema_v2.md`
- **Related tasks**: T046 (this playbook), T047 (governance update), T041 (perf harness).
- **Data retention**: Backfilled validation artifacts are retained under the same promotion policies enforced by `alphaforge-brain/src/services/retention/policies.py`.

Document owners should update this playbook whenever the manifest schema or validation SLA thresholds change.
