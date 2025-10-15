# Configuration Change Log

This log tracks schema-validated configuration updates for tolerance and retention policies.
Include a signed entry whenever configuration files change so CI can verify governance provenance.

- 2025-10-14: Initialized governance configuration baseline for `configs/trust_gates/tolerances/institutional_default.yaml`.
  Signed-off-by: governance-steward
- 2025-10-14: Initialized retention policy baseline for `configs/retention/policy.yaml`.
  Signed-off-by: governance-steward
- 2025-10-14: Updated `configs/trust_gates/tolerances/causality.yaml` with schema-required metadata fields.
  Signed-off-by: governance-steward
- 2025-10-15: Classified `zz_artifacts/journaling` as a full-run asset in `configs/retention/policy.yaml` (Decision 2) to inherit policy_version "2025.10.13" budgets.
  Signed-off-by: release-governance
- 2025-10-16: Updated `configs/trust_gates/tolerances/institutional_default.yaml` with journaling artifact requirements (schema 2025.10.16, canonical hash enforcement, waiver policy `journaling.artifact.required`).
  Signed-off-by: release-governance
