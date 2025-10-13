# Governance Hardening Checklist

**Scope**: Backend enforcement across AlphaForge Brain and Brain↔Mind integration contracts (Scope B per clarifications)

**Review Depth**: Release gate readiness (ensure promotability controls and documentation complete)

**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)

---

## Pre-Phase 1 Gate (Blocking)

- [x] Prereq files (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) verified present and current (2025-10-12)
- [x] Setup & foundational tasks (T001–T004) assigned to implementation lead for this iteration per `tasks.md`
- [x] Story ordering (US1 → US2 → US3) validated against dependency graph in `plan.md`

## Execution Tracking (Monitored Throughout Implementation)

The following milestones remain monitored via `tasks.md` and phase-specific validation logs:

### Trust Gate Tolerances (US1)
* Create and version causality tolerance profile alongside schema metadata (T008)
* Harden loader validation and fail-closed behavior with metrics/logging (T009–T012)
* Ensure validation pipeline and API propagation of `FAILED_VALIDATION` (T013–T015)

### Persistence & Accounting (US2)
* Synchronize persistence schema assets and enforce validation (T017–T022)
* Implement accounting invariants, logging, and API exposure (T023–T026)

### Retention & Import Guard (US3)
* Apply retention defaults, CLI tooling, and breach logging (T027–T034)
* Enforce runtime/lint import guards and document processes (T035–T037)

### Release Gate Evidence & Sign-off
* Capture benchmark evidence (T041–T043) and quickstart validation (T039)
* Maintain documentation, waiver inventory, and constitution proposals (T038–T044)
