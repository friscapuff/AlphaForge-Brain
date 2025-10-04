# CI Outline (FR-150–152)

Status: Planning Complete (Gate 0)

## Jobs & Steps
1. Lint & Type
   - ruff, mypy (baseline) + strict-plus allow-fail metrics append.

2. Unit & Integration Tests
   - pytest with asyncio defaults.

3. Schema Drift Check (FR-150)
   - Python step reads packaged migrations; computes expected head version/hash; compares to recorded constant or status file.
   - Fails if drift or missing migration.

4. Determinism Replay (FR-151)
   - Script runs two identical seeds; compares DB row counts and artifact hashes.
   - Emits summary and enforces equality gate.

5. Bootstrap CI Width Gate (FR-152)
   - Run minimal bootstrap trials (CI override: 200 @ 90%).
   - Fail STRICT mode if any monitored metric width exceeds threshold (env BOOT_CI_WIDTH_MAX).

6. Artifact Guard & Traceability
   - Block generated files from being tracked.
   - Echo SHA-256 of ARCH_MIGRATION_STATUS.md and poetry.lock for provenance.

---
Generated: 2025-09-24
