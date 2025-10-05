# Architecture Migration Status (AlphaForge Brain)

Date: 2025-09-24

Scope: Migration from legacy single-root to dual-root layout (alphaforge-brain/, alphaforge-mind/).

Repository: AlphaForge-Brain (branch: 004-alphaforge-brain-refinement)

Commit: 5edd67c60e5fa644209b944fe3cad17bb8f670e0

Exit Criteria

- [x] All code under legacy `src/` and `tests/` removed or shims documented
  - Evidence: tasks.md Gate A shows T009 completed; no legacy roots present in repo.
- [x] Cross-root integrity guard passes (Brain does not import Mind)
  - Evidence: scripts/ci/check_cross_root.py passes locally and wired in CI.
- [x] Deterministic parity maintained
  - Evidence: scripts/migration/verify_post_move.py retained (optional CI step allow-fail); tests pass; run hash semantics preserved in domain/run.
- [x] Tooling updated (mypy/ruff/pytest paths)
  - Evidence: pyproject, mypy.ini, pytest.ini, ruff config target alphaforge-brain/src; CI uses these paths.
- [x] Quality gates green (local validation)
  - Evidence: mypy 0 errors; ruff clean; pytest passing.
- [x] Documentation updated
  - Evidence: README and TESTING updated; tasks.md housekeeping section added (2025-09-24).

Artifacts

- Mypy snapshot (brain src): 0 errors (local)
- Ruff: All checks passed (local)
- Pytest: All tests passed (local)

Notes

- Optional strict-plus checks remain informational in CI with ratchet.
- Nightly parity run via verify_post_move is optional; step added as allow-fail placeholder.
