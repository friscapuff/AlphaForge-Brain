# API Versioning (Phase 1)

Current Policy (FR-031 / Clarification #6):
- OpenAPI `info.version` == package version.
- No custom headers; no URL version segment.
- Additive fields only; no breaking semantic changes.

Future Evolution (ISSUE-API-VERS-001):
- Phase 2 Trigger: Need preview endpoint → introduce `X-API-Preview: feature-id` header & documentation section.
- Phase 3 Trigger: Unavoidable breaking change → adopt Accept header media type: `application/vnd.alphaforge.v2+json`.

Consumer Guidance:
- Clients SHOULD treat unknown fields as non-breaking.
- Clients MAY pin to exact version if deterministic reproduction of UI snapshots required.

Change Log Requirements:
- Any new field: changelog fragment + schema diff test.
- Any preview feature: clearly labeled experimental; removal allowed until promoted.
