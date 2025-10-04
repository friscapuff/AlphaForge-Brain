# Testing & Determinism Guide

This document centralizes conventions, fixtures, and patterns for writing and maintaining the AlphaForge Brain test suite.

## Goals
- Zero flake baseline: any failure must indicate a real regression.
- Deterministic reproducibility: identical code + config + dataset => identical artifacts & metrics.
- High signal: minimal boilerplate, explicit intent, clear failure diffs.
- Fast feedback: unit tests <1s, integration <5s local (target), perf tests opt-in.

## Test Taxonomy
| Layer | Folder | Purpose | Example Topics |
|-------|--------|---------|----------------|
| Contract | `tests/contract/` | Public API & schema stability | POST /runs, SSE event order |
| Integration | `tests/integration/` | Multi-component flows & artifact cohesion | Deterministic replay, anomaly counters |
| Unit | `tests/unit/` | Pure logic & edge math | Costs, hashing, walk-forward segmentation |
| Performance | `tests/perf/` | Timing guardrails (opt-in locally / CI gated later) | Baseline run latency |

## Core Fixtures
| Fixture | File | Description |
|---------|------|-------------|
| `freeze_time` | `tests/conftest.py` | Replaces module-level `datetime` with subclass overriding `now/utcnow` for exact timestamp assertions. |
| `random_seed_fixture` | `tests/conftest.py` | Seeds `random` and provides canonical seed for engines needing explicit seed parameter. |
| NVDA dataset fixtures | `tests/data/nvda_fixtures.py` | Canonical NVDA slices & hashes for provenance tests. |

### freeze_time Details
Implementation injects a `FrozenDateTime` subclass into project modules only, avoiding mutation of the builtin C type. Use when asserting:
- `manifest.created_at`
- SSE event timestamps (exact match or prefix w/ explicit reason)

Do NOT call `datetime.utcnow()` directly in new code—always use `datetime.now(timezone.utc)`; the fixture overrides both.

### RNG Control
All randomness must be explicit:
- Functions performing shuffles / sampling accept a `seed: int | None` parameter.
- Tests rely on `random_seed_fixture` instead of ad-hoc literals.
- Derive sub-seeds (e.g., permutation trials) via simple deterministic transformation: `base_seed + k`.

If true nondeterminism is intentional, document with `# nondeterministic-by-design` explaining rationale.

## Factories
`tests/factories.py` supplies helpers for frequently constructed models (`run_config`, `walk_forward_variant`, `trade`, etc.). Extend instead of duplicating inline dicts. Always maintain timezone-aware datetimes in defaults.

## Walk-Forward Segmentation Testing
`test_walk_forward_splits.py` parameterizes multiple (train, test, warmup, total) combinations. Expected segment count is computed algorithmically:
```
count = 0
i = 0
while i + (train + test) <= total:
    count += 1
    i += test
```
Edge Case: If `total < train + test` result is `[]` (no segment); tests explicitly allow this.

## Manifest & Artifact Assertions
- Prefer strict equality on lists of artifact descriptors (name, hash, path) unless order intentionally unspecified (then sort before compare).
- When hashing collections for comparison, ensure stable ordering (e.g., sort by `name`).

## Event Stream Testing
SSE tests assert:
- Monotonic incremental IDs.
- Phase ordering (start → data → features → strategy → risk → execution → metrics → validation → artifacts_finalized → completed).
- Heartbeat interval does not exceed configured threshold (fixture uses frozen time; logic compared via counters rather than wall clock drift).

## Adding New Tests Checklist
1. Identify layer (unit vs integration vs contract).
2. If using time or randomness, import the needed fixture in signature.
3. Use factories for model construction.
4. Parameterize when covering dimension-like variations (sizes, windows, seeds) rather than duplicating functions.
5. Run `pytest -q`; ensure no warnings. pytest-asyncio defaults are pinned in `pytest.ini` to silence deprecation warnings:
    - `asyncio_mode = auto`
    - `asyncio_default_fixture_loop_scope = function`
6. Run `mypy` if new types added to models/services.

## Performance Tests (Future Gating)
Perf tests live under `tests/perf/` and SHOULD be skipped by default locally unless `PERF=1` environment variable is set (planned). They will establish regression thresholds before gating CI.

## Lint & Type Discipline
- All new Python files must pass `ruff` (format + lint) and mypy strict.
- Avoid `# type: ignore`; if unavoidable, justify with an inline comment referencing an issue.

## Common Pitfalls
| Pitfall | Avoidance |
|---------|-----------|
| Using unstable float repr in hash inputs | Use canonical hash utilities already provided. |
| Relying on implicit ordering of dicts for test expectations | Sort keys or compare sets appropriately. |
| Hidden timezone-naive datetimes | Always use `timezone.utc` aware instances in runtime layer. |
| Intermittent timestamp comparisons | Use `freeze_time` and assert equality. |

## Roadmap Enhancements
- Snapshot diff for OpenAPI & artifact schema.
- pytest plugin for automatic seed derivation tracing.
- Unified `numpy.random` and `pandas` RNG seeding fixture (added when functionality depends on them).

## Contributing
Ensure any doc change reflecting test behavior also updates:
- README Section 7 / 7.a
- CHANGELOG unreleased section
- tasks.md rationale table (if infrastructure-level change)

Note: CI uploads coverage/timing artifacts, but these are not committed locally (`coverage.xml`, typing timing files, and similar are in `.gitignore`).

Happy testing – deterministic by default.

## New Test Additions (Feature 006 Enhancements)

### Artifact Retrieval & Formats
New integration tests exercise the `/runs/{run_hash}/artifacts` and `/runs/{run_hash}/artifacts/{name}` endpoints covering three branches:
- Whitelisted JSON artifact (`metrics.json`) – validated for exact parsed structure.
- Generic Parquet artifact (`frame.parquet`) – endpoint returns `{columns, row_count}` metadata.
- Raw bytes fallback (`raw.bin`) – endpoint returns opaque bytes (serialization may appear as either raw bytes or a JSON stringified form; tests allow both for portability).

Key behaviors:
- Artifact listing intentionally filters to an allowlist (e.g., `metrics.json`, `equity.parquet`); non-whitelisted files (like `frame.parquet`) won’t appear but can still be fetched directly.
- Tests register synthetic runs by inserting records into `app.state.registry` to avoid invoking full orchestration when only retrieval branches are needed.

### Retention Demotion via Byte Budget
`test_retention_demotion_bytes.py` forces demotion by:
1. Creating multiple synthetic runs with ~1KB artifacts each.
2. Applying a `RetentionConfig` with `max_full_bytes` < total aggregate, ensuring at least one run transitions to `manifest-only`.
3. Asserting demotion vs full states without depending on specific ordering beyond newest likely remaining full.

### Multi-Field Validation Aggregation
`test_validation_multiple_fields.py` triggers a `RequestValidationError` on the versioned `/api/v1/backtests` endpoint and asserts:
- HTTP 400 (the versioned endpoint maps validation errors to 400 instead of FastAPI’s default 422).
- Aggregated distinct field names (at least two) captured in the error envelope.

### Monte Carlo Extended Percentiles & Rate Limiting
Existing tests (`test_phase_3_3b_backend_tests.py`) already cover:
- `extended_percentiles=True` branch (validating `p5` / `p95`).
- Global Monte Carlo rate limiting (burst beyond limit yields at least one 429).
No duplicate tests were added—coverage achieved through original feature suite.

## Marker Usage Quick Reference
Markers now registered in `pytest.ini`:

| Marker | Use Case | Example |
|--------|----------|---------|
| `artifacts` | Artifact format & retrieval | `pytest -m artifacts -q` |
| `retention` | Retention policy & demotion | `pytest -m retention -q` |
| `feature006` | Versioned backtests & MC percentiles | `pytest -m feature006 -q` |

Run only new additions:
```bash
pytest -m "artifacts or retention" -q
```

## Hang / Stall Diagnosis Workflow
If a full-suite run appears to stall:
1. Use the slice runner script:
    ```bash
    python scripts/run_test_slices.py 120
    ```
    This writes `test_slice_results.json` summarizing each test directory’s status (pass/fail/timeout) and duration.
2. Re-run the offending slice with verbose timing:
    ```bash
    pytest -vv <directory> --durations=25
    ```
3. If a fixture blocks, add a per-test timeout (plugin already enabled via `--timeout=120`).
4. For SSE or streaming endpoints, ensure the client call uses explicit timeouts or that the server emits terminal events.

## Coverage Strategy
`pytest.ini` now includes:
```
--cov=alphaforge-brain/src --cov-report=term-missing --cov-report=xml
```
This produces a `coverage.xml` artifact (ignored by VCS) for tooling (quality gates, CI badges). When adding new tests, prefer targeting uncovered branches (use `term-missing` output to locate gaps). Keep fast, focused tests for logic branches; integration tests should avoid unnecessary large data generation.

## Future Improvements
- Auto-mark long-running slices (`> N seconds`) as `slow` in the slice runner output for selective exclusion.
- Add a JSON schema validation step for artifact metadata to guard accidental shape drift.
- Integrate slice runner into CI fallback path if a baseline duration threshold is exceeded.

## Current Coverage Snapshot & Gap Plan (automated pass)
Date: 2025-09-27 (full-suite + slice aggregation)

Overall line coverage: ~81% (aggregate after slice merge)

Recently uplifted (now healthy >=85% or functionally exercised):
- `api.routes.runs` (mid → high 80s) via idempotency, listing, artifact retrieval tests
- `domain.run.orchestrator` (~90%) through new SSE edge + idempotency tests
- `domain.run.retention` & `retention_policy` (≥94%) via pruning & demotion scenarios
- Validation algorithms (most ≥90%) through expanded walk-forward & permutation coverage

High-impact LOW coverage modules (priority tiers):
Tier 1 (core runtime logic, currently ≤0–30% or critical untested branches):
- `domain.run.async_orchestrator` (0%) – legacy / alt path; either deprecate or add parity tests mirroring synchronous orchestrator path. ACTION: Decide keep vs remove; if kept, add a minimal happy-path + cancellation test using an async stub strategy.
- `services.equity`, `services.metrics`, `services.execution` (0%) – pure service façade logic. ACTION: Unit tests mocking lower layers to assert orchestration/aggregation results & error propagation.
- `infra.credentials` (0%) – placeholder? ACTION: If intentional stub, mark with `# pragma: no cover` or add minimal parse/validation test.
- `infra.utils.time` (0%) – functions unused? Either mark `no cover` or add deterministic tests with `freeze_time` verifying conversions.
Tier 2 (medium complexity, partial coverage 50–80% with uncovered branches meaningful for correctness):
- `services.chunking` (≈61%) – missing error/edge branches: empty input, oversize batch, remainder handling. ACTION: Add parameterized unit tests with small synthetic arrays.
- `domain.metrics.calculator` (76%) – uncovered percentile / edge division paths. ACTION: Inject deterministic inputs capturing zero-trade, single-trade, and high-volatility scenarios.
- `domain.features.engine` (83%) – remaining gaps around feature dependency resolution fallbacks. ACTION: Add tests with intentionally missing feature to assert error classification.
- `infra.cold_storage` (66%) – uncovered error handling branches (missing archive member, checksum mismatch). ACTION: Create malformed tar in temp dir and assert raised exceptions.
Tier 3 (models / DTOs with largely declarative fields):
- `models.summary_snapshot`, `models.walk_forward`, etc. Many lines show as 0% because runtime construction occurs only in long E2E flows. ACTION: Either: (a) build lightweight factory-driven instantiation tests; or (b) annotate trivial pydantic models with `# pragma: no cover` if they are purely declarative containers.

Deprecation / Prune Candidates:
- If `async_orchestrator` is superseded by sync orchestrator + event buffer, prefer removal to chasing coverage.
- Any unused legacy models under `models.*` not referenced by API or persistence should be deleted or migrated.

Planned Next Test Wave (ordered):
1. Decide keep/remove: `async_orchestrator` (PR: removal or add 2 tests) – ownership: runtime maintainer.
2. Add unit tests for `services.metrics` & `services.equity` validating aggregation math & empty-input edge.
3. `services.execution` – simulate minimal execution cycle with fake state; assert emitted trades and error branch.
4. `services.chunking` – parameterized test for (exact division, remainder, single element, zero items).
5. `infra.cold_storage` negative path – malformed tar & missing member.
6. `infra.utils.time` – add coverage or mark no-cover if purely transitional.
7. Metrics calculator edge branches (zero trades / all losses / all gains) to push to ≥90%.

Coverage Hygiene Conventions:
- For modules intentionally excluded (pure enum / data shapes), use `# pragma: no cover` per line or mark entire file in `pyproject.toml` `tool.coverage.run.omit` when justified.
- Favor small, isolated unit tests over extending long integration scenarios.
- Each added test targeting a gap should reference the module & branch in a short comment, e.g.: `# coverage: services.chunking remainder branch`.

Open Questions (to resolve before next cycle):
- Are async orchestration paths part of future scaling roadmap? If not, remove to reduce maintenance surface.
- Should credential resolution remain runtime-loaded or move to config-time (allowing simpler testing)?

Once Tier 1 & Tier 2 addressed, projected coverage: 88–90% (assuming selective pruning / pragmas for pure models).
