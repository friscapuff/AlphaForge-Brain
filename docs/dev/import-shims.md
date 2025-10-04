# Import Shims and Legacy Package Compatibility

This project maintains a dual layout where implementation code lives under `src/` but
historical tests and modules still import top-level packages like `infra.*` directly.
Some test runners prepend the repository root ahead of `src` on `sys.path`, causing
Python to resolve the *root* `infra/` package (a lightweight shim) instead of
`src/infra/`.

## Why Shims Exist

1. Preserve backwards compatibility for older absolute imports (`from infra.time...`).
2. Allow incremental migration without breaking existing suites.
3. Support Windows path / filename constraints (e.g., cache filenames replacing `:` with `_`).
4. Avoid brittle `PYTHONPATH`/`sys.path` manipulations inside every test.

## Current Shim Strategy

- Root `infra/__init__.py` inserts `src` at the front of `sys.path` and extends its
  `__path__` to include `src/infra` so all submodules resolve.
- Explicit pre-import of critical subpackages (`infra.time`, `infra.cache`) warms
  module objects for subsequent attribute access.
- Root `infra/cache/*.py` provides thin forwarders (`features.py`, `metrics.py`, `candles.py`)
  to mirror implementations in `src/infra/cache`.

## Guard Tests

`tests/imports/test_infra_cache_shim.py` ensures:
- Legacy imports succeed (`from infra.cache import CandleCache`).
- Basic cache roundtrip works and metrics increment.
- Generated parquet filenames are Windows‑safe (no `:` characters).

## Maintenance Guidelines

Whenever you add a new submodule under `src/infra/...` that older code might import
(as `infra.*`), ensure one of the following:
- The root `infra/__init__.py` path extension already covers it (most cases), or
- Provide a forwarding shim file under the root `infra/` tree if name conflicts arise.

## Adding New Shims

1. Create the implementation under `src/infra/<subpkg>/module.py`.
2. If legacy imports will use `infra.<subpkg>.module`, normally **no action** needed since
   `__path__` extension handles it.
3. If a name collision or import ordering issue appears, add a forwarding module
   `infra/<subpkg>/module.py` that re-exports the symbols.
4. Add / update a guard test in `tests/imports/`.

## Future Decommission Plan

Once all legacy absolute imports are refactored to explicit `src.` or equivalent
(relative) imports, the root shim can be simplified or removed. Before removal:
- Run the guard tests.
- Search for `from infra.` patterns outside `src/infra` to confirm none rely on shim.

## Troubleshooting

| Symptom | Likely Cause | Remedy |
|---------|--------------|-------|
| `ModuleNotFoundError: infra.cache.features` | Root shim resolved but forwarding file missing | Add root shim module or update `__path__` logic |
| Mixed implementation modules (some from root, some from src) | `sys.path` ordering changed externally | Ensure `src` is inserted at index 0 in `infra/__init__.py` |
| Filename OSError on Windows for cache | Colons in key-derived filenames | Use underscore replacement like in `infra.cache.candles` |

---
Generated automatically as part of the import shim hardening task.

## Timestamp Edge-Case Testing Note

Although timestamp conversion lives under `src/infra/time/`, the legacy `infra.time` import path
is still exercised by older code. We added explicit regression tests covering:

- Multi-row localization with `assume_tz` ensuring length preservation (`test_timestamps_regression.py`).
- DST fall-back ambiguous hour mapping to `NaT` when `ambiguous='NaT'`.
- DST spring-forward nonexistent hour handling (both `shift_forward` and `NaT` strategies).

Rationale:
- Guard against silent behavioral drift in shim-mediated imports (a past bug only appended the final element).
- Demonstrate deterministic, side-effect free conversions even through legacy import paths.

If future refactors remove the shim, keep these tests pointing at `infra.time.timestamps` (they'll continue to
resolve through the updated module path) until migration is complete—then relocate or adjust imports in the tests.
