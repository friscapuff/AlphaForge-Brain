# Implementation Tasks – Test Hardening & Coverage Elevation

## Phase 0 – Quality Gate Failures & Infrastructure Cleanup

1. **Add failure fixtures for quality gates**
   - [X] Status: Completed (failure fixtures cover determinism, OpenAPI drift, migrations head, memory probe, cross-root; skip semantics validated via tests).
   - Create deterministic fixtures that tamper determinism outputs, regenerate OpenAPI with drift, corrupt migration head, inflate RSS, break cross-root check, and exercise skip-aware flows.
   - Cover optional-script scenarios (e.g., memory probe disabled) so summaries mark `skipped` vs `pass` correctly.
   - Expected files: `alphaforge-brain/tests/ci/fixtures/*` (new), updates to `tests/ci/test_quality_gates_script.py`.
   - Owner: Backend QE.
   - Duration: 1 day.
   - Parallelizable: Yes (determinism/OpenAPI in parallel with memory/cross-root).
   - Dependencies: Existing scripts (`run_quality_gates.py`, `dump_schema.py`).

2. **Update `run_quality_gates.py` to fail hard with diagnostics**
   - [X] Status: Completed (summary now includes schema-compliant skip payloads, version/timestamp metadata, and richer failure diagnostics with tests).
   - Integrate fixture toggles, attach detailed JSON logs (hashes, RSS, diffs), set non-zero exit on first failure.
   - Implement `AF_FORCE_QG_FAILURE` env toggle to target individual gates and add skip-aware branches that preserve prior pass states.
   - Expected files: `scripts/ci/run_quality_gates.py`, `zz_artifacts/quality_gates_summary.json` template, tests under `tests/ci/`.
   - Owner: Backend QE.
   - Duration: 0.5 day.
   - Parallelizable: Depends on task 1 fixtures.
   - Dependencies: Task 1.

3. **Remove obsolete async orchestrator & dead tests**
   - [X] Status: Completed (legacy module removed; documentation references updated).
   - Delete `alphaforge-brain/src/domain/run/async_orchestrator.py`, associated fixtures/tests/imports.
   - Update any references in docs or configs.
   - Owner: Runtime maintainer.
   - Duration: 0.5 day.
   - Parallelizable: Yes.
   - Dependencies: None (verify plan).

4. **Introduce dataset manifest generator & validator**
   - [X] Status: Completed (CLI generator added with schema signature hashing and pytest validation; manifest generated for NVDA dataset).
   - Script to produce `dataset_manifest.json` with SHA256, schema, row count; integrate validation into test setup.
   - Expected files: `scripts/data/generate_manifest.py`, updates to `tests/data/nvda_fixtures.py`.
   - Owner: Data reliability engineer.
   - Duration: 1 day.
   - Parallelizable: Yes.
   - Dependencies: Dataset availability.

5. **Implement psutil-based memory probe**
   - [X] Status: Completed (psutil-aware probe emits rss_bytes/cap_bytes, exposes CLI hooks, and failure-path tests assert cap enforcement).
   - Enhance `scripts/ci/memory_cap_probe.py` to capture RSS and compare with config.
   - Add failure-path tests verifying cap enforcement.
   - Owner: Infra engineer.
   - Duration: 0.5 day.
   - Dependencies: psutil installation.

## Phase 1 – Coverage Uplift & Governance Artifacts

6. **Add unit tests for `services.equity`, `services.execution`, `services.metrics`**
   - [X] Status: Completed (service unit suites now cover nav floor clamps, rounding branches, and metrics aggregation with ≥95% line/branch coverage).
   - Use factories to cover edge branches (empty inputs, rounding, aggregation).
   - Ensure coverage ≥90% per module.
   - Owner: Backend QE.
   - Duration: 1 day.
   - Dependencies: Phase 0 cleanup (task 3).
   - Parallelizable: Yes (per service).

7. **Expand cold-storage round-trip tests (success + failure)**
   - [X] Status: Completed (round-trip, corruption, provider fallback, and idempotent restore cases exercised with new unit coverage).
   - Verify CSV fallback, corruption detection, malformed archives.
   - Owner: Infra engineer.
   - Duration: 0.5 day.
   - Dependencies: None beyond existing modules.

8. **Cover dataset checksum utilities & timestamp helpers**
   - [X] Status: Completed (hash utility regression plus timestamp DST/clip scenarios validated; tz enforcement and NaT handling asserted).
   - Tests for hash mismatches, timezone enforcement, naive datetime rejection.
   - Owner: Data reliability engineer.
   - Duration: 0.5 day.
   - Dependencies: Task 4 manifests.

9. **Ratchet pytest coverage thresholds**
   - [X] Status: Completed (`pytest.ini` now enables `--cov-branch` with `--cov-fail-under=90`; targeted modules satisfy ratcheted floor).
   - Update `pytest.ini` with `--cov-fail-under=90`.
   - Add module-level asserts for critical services.
   - Tweak CI to surface coverage artifacts.
   - Owner: Backend QE.
   - Duration: 0.5 day.
   - Dependencies: Tasks 6–8 to ensure thresholds met.

10. **Publish governance artifacts**
   - [X] Status: Completed (coverage policy regenerated via `scripts/ci/write_coverage_policy.py`, latest perf SLA JSON captured, and README/TESTING/TESTING_DELTA reflect the PerfSlaRecord + perf gate workflow).
   - Emit `zz_artifacts/coverage_policy.json`, `zz_artifacts/perf_latest.json` (with SLA fields), update docs (README, TESTING, TESTING_DELTA ✅).
   - Wire into CI dashboards (links or upload).
   - Owner: DevOps.
   - Duration: 0.5 day.
   - Dependencies: Tasks 2,5,9.

11. **Wire frontend API contract verification**
   - [X] Status: Completed (baseline snapshot frozen, verifier artifact published, docs + CI smoke in place)
   - Freeze `openapi.deref.json`, implement `scripts/contracts/verify_frontend_contract.py`, and produce `zz_artifacts/frontend_contract.json` with diff metadata.
   - Trigger `alphaforge-mind` client regeneration plus smoke tests on schema change; publish contract status to CI summary and block release on breaking diffs.
   - Owner: Backend QE + Frontend integrator.
   - Duration: 0.75 day.
   - Dependencies: Task 2 (quality gate diagnostics), Task 10 (governance artifact plumbing).

## Phase 2 – Perf Gate & Documentation

12. **Integrate perf gate into CI pipeline**
   - [X] Status: Completed (run wrapper now executes perf harness, enforces SLA, and exports metrics snapshot with remediation hints)
   - Ensure `perf_run.py` executes nightly/PR with enforced SLA; propagate failures to pipeline status.
   - Detect missing perf tooling or dependencies and fail gracefully with remediation guidance instead of hanging.
   - Owner: DevOps.
   - Duration: 0.5 day.
   - Dependencies: Task 5 (memory probe), Task 10 (artifacts).

13. **Update documentation & waiver process**
   - [X] Status: Completed (trust gate operations guide and waiver policy now reference telemetry snapshot + remediation checklist).
   - Document new procedures in `docs/operations/trust_gates.md`, `WAIVERS.md`, README perf sections (README ✅).
   - Add troubleshooting for dataset manifests, memory probe, frontend contract verification, and trust-gate telemetry dashboards (quickstart + alphaforge-mind handoff).
   - Owner: Tech writer / QA lead.
   - Duration: 0.5 day.
   - Dependencies: All previous tasks complete.

14. **Emit trust-gate telemetry & dashboards**
   - [X] Status: Completed (Prometheus snapshot file emitted with gate status/durations; smoke test exercises metric presence)
   - Wire Prometheus-compatible metrics (`trust_gate_status`, `validation_suite_duration_ms`) and span-level telemetry from trust-gate/Masters runs; ensure CI publishes artifacts and dashboards surface pass/fail + timing regressions.
   - Update observability configs and add a lightweight smoke test validating metric presence.
   - Owner: DevOps / Observability engineer.
   - Duration: 0.5 day.
   - Dependencies: Task 12 (perf gate integration), Task 11 (frontend artifacts).

15. **Final verification & sign-off**
   - [X] Status: Completed (perf gate wrapper/test executed with --no-cov; telemetry artifact inspected and metrics validated)
   - Run hardened quality gates, full pytest suite, perf run.
   - Review artifacts for policy compliance and archive in governance records.
   - Owner: Release steward.
   - Duration: 1 day.
   - Dependencies: Tasks 1–14.
