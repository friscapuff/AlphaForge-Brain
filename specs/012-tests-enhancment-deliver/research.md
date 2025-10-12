# Research Notes – Test Hardening & Coverage Elevation

## Decision 1: Failure-path fixtures over ad-hoc mocking
- **Decision**: Build dedicated fixtures that mutate determinism artifacts, OpenAPI dumps, migration heads, memory usage, and cross-root state to exercise each quality gate failure branch.
- **Rationale**: Realistic fixtures avoid brittle mocks, keep determinism guardrails intact, and allow reuse across future regressions.
- **Alternatives Considered**: (a) Mock subprocess/JSON outputs directly, but this risks diverging from actual script behavior; (b) Manually editing artifacts during CI, which is slower and harder to reset.

## Decision 2: Capture RSS via `psutil`
- **Decision**: Integrate `psutil.Process().memory_info().rss` into `memory_cap_probe.py` to collect peak RSS during gate execution.
- **Rationale**: `psutil` is cross-platform, already compatible with the project’s Python 3.11 stack, and avoids platform-specific `resource` limits unavailable on Windows.
- **Alternatives Considered**: (a) Python `resource` module—Linux-only and unavailable on Windows; (b) External CLI tools (`/usr/bin/time`) that complicate automation.

## Decision 3: Dataset manifest hashing
- **Decision**: Generate `dataset_manifest.json` files per canonical dataset containing SHA256, schema signature, and row count, validated before fixtures run.
- **Rationale**: Hash manifests provide tamper detection without shipping large binaries and align with existing artifact integrity workflows.
- **Alternatives Considered**: (a) Embedding CSV snapshots into tests—bloats repo; (b) Relying on timestamp checks—fails to detect content drift.

## Decision 4: Enforce ≥90% coverage via pytest + module checks
- **Decision**: Increase global `--cov-fail-under` to 90 and add targeted assertions for critical modules (services, infra) to keep local coverage honest.
- **Rationale**: Global threshold prevents silent regressions, while module assertions ensure new surfaces stay above target even if total coverage is padded by legacy code.
- **Alternatives Considered**: (a) Relying on code-climate dashboards (delayed feedback); (b) Manual reviewer enforcement (human error-prone).

## Decision 5: Publish perf & coverage governance artifacts
- **Decision**: Emit machine-readable `CoverageThresholdPolicy.json` and `PerfSlaRecord.json` artifacts during CI.
- **Rationale**: Provides auditable trail for waivers, supports dashboards, and satisfies governance requirements outlined in the spec.
- **Alternatives Considered**: (a) Document-only approach—difficult to automate; (b) Embedding metadata in logs—harder for tooling to parse.

## Decision 6: Guard frontend contract drift with automated diffing
- **Decision**: Introduce a contract verification script that freezes the OpenAPI snapshot, diffs it against the committed baseline, regenerates the `alphaforge-mind` TypeScript client, and runs smoke tests on schema change.
- **Rationale**: Ensures backend schema shifts are caught before rollout, keeps frontend artifacts deterministic, and aligns with release gating for cross-team consumers.
- **Alternatives Considered**: (a) Manual coordination via Slack updates—slow feedback and prone to misses; (b) Relying solely on contract tests in frontend repo—misses backend-only releases without concurrent frontend changes.

No outstanding clarifications remain after this research phase.
