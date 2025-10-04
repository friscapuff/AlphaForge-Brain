# AlphaForge Brain

Backend simulation & analytics core (migrated from legacy single-root `src/`).

Transition Phase Notes:
- All existing domain, api, infra, services code moves under `alphaforge-brain/src/`
- Determinism baseline must match pre-move hashes.
- Legacy `src/` will be removed post-verification.

## Retention Metrics API

Endpoint: `GET /retention/metrics`

Returns JSON structure summarizing logical retention state counts and on-disk byte usage of active artifacts (excludes `manifest.json` and the `.evicted` directory contents):

```
{
	"api_version": "0.1",
	"counts": {
		"full": 12,
		"pinned": 3,
		"top_k": 4,
		"manifest-only": 21,
		"total": 40
	},
	"bytes": {
		"full": 104857600,
		"pinned": 5242880,
		"top_k": 10485760,
		"manifest-only": 0,
		"total_bytes": 120083,    // Sum of the above categories
	},
	"max_full_bytes": 2147483648,      // Optional configured cap (may be null)
	"budget_remaining": 2032626048     // max(0, max_full_bytes - bytes.full) or null if uncapped
}
```

Field semantics:
- `counts.full` – Runs currently retained with full artifacts (not pinned/top_k demoted).
- `counts.pinned` – Runs explicitly pinned (immune to demotion).
- `counts.top_k` – Strategy top-K preserved runs.
- `counts.manifest-only` – Demoted runs containing only manifest + summary metadata.
- `counts.total` – Aggregate of all states.
- `bytes.<state>` – Summed file sizes of retained artifact files for that state (excludes manifest + placeholder markers).
- `bytes.total_bytes` – Sum of the four principal state byte totals.
- `max_full_bytes` – Configured soft ceiling for cumulative `full` state bytes. When exceeded, additional older full runs become eligible for demotion.
- `budget_remaining` – Remaining byte budget for additional full runs (`None` if no ceiling configured).

Update retention settings via `POST /settings/retention` with any subset of:
```
{
	"keep_last": 50,
	"top_k_per_strategy": 5,
	"max_full_bytes": 1073741824
}
```

After updating settings you can trigger computation & physical demotion with `POST /runs/retention/apply` (automatic on setting change as well).

### Dry-Run Retention Plan

`GET /retention/plan` returns the computed plan (keep_full, demote, pinned, top_k, summary counts) without applying demotions. Use this for UI previews.

### Audit Log Rotation & Integrity

Audit events append to `artifacts/audit.log`. Rotation occurs when size exceeds `AF_AUDIT_ROTATE_BYTES` (default 1MB). Rotated files are gzip-compressed (`audit.log.<epoch>.gz`) and an `audit_integrity.json` snapshot records the last hash and rotated filename. Each audit line has a `hash` and `prev_hash` enabling chain verification.

### Cold Storage Placeholder

Module `infra/cold_storage.py` introduces a stub for future offloading of evicted artifacts. When `AF_COLD_STORAGE_ENABLED=1` (no-op currently) the offload hook would stream evicted files to external storage and mark them `.offloaded` locally.

## Parquet Optionality & Fallback (Developer Notes)

The project treats parquet support (pyarrow / fastparquet) as optional so a minimal Python environment can still run tests and basic flows.

Key behaviors:

- Caches & artifacts always create files with a `.parquet` extension for deterministic naming.
- If a parquet engine is unavailable or fails at runtime (e.g. binary/NumPy ABI mismatch), we transparently write CSV bytes under the `.parquet` filename and emit a one-time structured warning log (`cache_parquet_fallback`).
- Reads attempt true parquet first; on failure they fall back to CSV parsing.

Helper utilities:

- `infra.cache._parquet`: Centralized availability probe (`parquet_available()`), lazy module load, and one-time fallback logging.
- `lib.artifacts.read_parquet_or_csv(path: Path) -> DataFrame`: Unified best-effort reader used by the API layer and tests to eliminate duplicated try/except parquet-vs-CSV logic.

Diagnostics:

- Run `python -m infra.cache.doctor` to inspect parquet availability, version (if present), and a quick classification of cache file encodings.

Testing considerations:

- Integration tests purposely exercise both the parquet and CSV fallback pathways; the unit test `tests/unit/test_artifacts_read_helper.py` isolates the helper behavior with a forced CSV-under-parquet scenario.
- When adding new parquet writes, prefer delegating to existing helpers (`write_parquet` in `lib.artifacts` or cache layer methods) so fallback semantics remain consistent.

Future refinement:

- If additional modules outside artifacts/API start performing ad‑hoc parquet reads, consider refactoring them to depend on `read_parquet_or_csv` for uniform behavior.

Developer guardrail:

- A local pre-commit hook (`forbid-raw-parquet`) blocks new direct `pd.read_parquet(` usages to encourage the resilient helper. If a direct parquet read is truly required (e.g. performance-critical path where CSV fallback would be misleading), append a justification comment token `# parquet-ok: reason`. Example:

	```python
	table = pd.read_parquet(path)  # parquet-ok: fast metadata access, fallback handled earlier
	```

- Run manually with `pre-commit run forbid-raw-parquet --all-files`.
