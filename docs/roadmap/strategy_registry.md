# Strategy Registry Governance Roadmap (Placeholder – FR-045)

Status: Placeholder stub for future governance expansion (Task T078).

This document will define:
- Acceptance workflow for new strategies (metadata: strategy_id, parameter hash, acceptance_reason, rejection_reason).
- Governance policies to mitigate survivorship and graveyard bias.
- Criteria for deprecation and archival.
- Audit fields surfaced in manifest and summary outputs.

Current Release Scope:
- Optional strategy metadata fields recorded if provided (see services/strategy_registry.py).
- No governance workflows or multi-strategy evaluation pipelines implemented yet.

Future Iterations (Not Implemented Yet):
1. Multi-strategy evaluation batch mode with comparative robustness scores.
2. Metadata provenance ledger (who approved, timestamp, rationale).
3. Automated parameter space exploration tracking and rejection heuristics.
4. Registry pruning and lifecycle states (proposed/accepted/deprecated/archived).

Determinism Note:
All eventual registry expansions must preserve run_hash determinism: metadata inclusion rules must be explicit and order-independent.

---
Generated: 2025-09-23
