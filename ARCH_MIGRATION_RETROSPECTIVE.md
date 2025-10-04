# Architecture Migration Retrospective

Date: 2025-09-24

Scope: Single-root to dual-root (alphaforge-brain/, alphaforge-mind/) migration completion.

What went well
- Clear task breakdown (Gate A) with explicit exit criteria.
- Strict typing and linting caught edge cases early; zero-error baseline achieved.
- CI overlays for strict-plus provided visibility without blocking velocity.

What was hard
- Managing transient artifacts and ensuring no CI inputs depended on local files.
- Optional plotting dependency typing required careful handling to satisfy strict mypy.

Risks & Mitigations
- Risk: Cross-root import drift.
  - Mitigation: `scripts/ci/check_cross_root.py` + CI gating.
- Risk: Determinism regression during file moves.
  - Mitigation: Baseline capture/verify scripts; seed discipline.

Recommendations
- Keep artifacts out of repo root; use `artifacts/` or `zz_artifacts/`.
- Promote strict-plus to baseline after a stable period and address any residual overlays.
- Consider nightly parity checks for long-lived branches.
