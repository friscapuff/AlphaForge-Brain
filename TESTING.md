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
